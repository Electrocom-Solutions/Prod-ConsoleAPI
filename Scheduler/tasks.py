"""
Celery tasks for the Scheduler app.
"""
from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
from calendar import monthrange
import logging

from HR.models import Employee, PayrollRecord
from AMC.models import AMC, AMCBilling
from Tenders.models import Tender, TenderDeposit
from Notifications.models import Notification
from Notifications.utils import send_notification_to_owners
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='Scheduler.tasks.generate_monthly_payroll')
def generate_monthly_payroll(self):
    """
    Generate monthly payroll records for all employees.
    
    This task runs daily at 11:00 PM and only generates payroll records
    on the last day of the month.
    
    The task:
    1. Checks if today is the last day of the month
    2. Ensures idempotency (doesn't create duplicate records)
    3. Creates payroll records for all employees in a transaction
    4. Calculates working days and days present based on attendance records
    """
    try:
        # Get current date in Asia/Kolkata timezone
        from django.utils import timezone as tz
        import pytz
        
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        now = tz.now().astimezone(kolkata_tz)
        today = now.date()
        
        # Check if today is the last day of the month
        last_day = monthrange(today.year, today.month)[1]
        if today.day != last_day:
            logger.info(f"Today ({today}) is not the last day of the month. Skipping payroll generation.")
            return {
                'status': 'skipped',
                'reason': 'Not the last day of the month',
                'date': str(today)
            }
        
        logger.info(f"Starting monthly payroll generation for {today.year}-{today.month:02d}")
        
        # Calculate period dates for the current month
        period_from = date(today.year, today.month, 1)
        period_to = date(today.year, today.month, last_day)
        
        # Get system user for created_by field (or create a default admin user)
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            logger.warning("No superuser found. Payroll records will have null created_by.")
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Get all active employees
        employees = Employee.objects.select_related('profile', 'profile__user').all()
        
        if not employees.exists():
            logger.warning("No employees found. Skipping payroll generation.")
            return {
                'status': 'skipped',
                'reason': 'No employees found',
                'date': str(today)
            }
        
        with transaction.atomic():
            for employee in employees:
                try:
                    # Check if payroll record already exists for this employee and month
                    existing_payroll = PayrollRecord.objects.filter(
                        employee=employee,
                        period_from__year=today.year,
                        period_from__month=today.month
                    ).first()
                    
                    if existing_payroll:
                        logger.info(f"Payroll record already exists for employee {employee.employee_code} "
                                  f"for {today.year}-{today.month:02d}. Skipping.")
                        skipped_count += 1
                        continue
                    
                    # Calculate working days (excluding weekends and holidays)
                    # This is a simplified calculation - you may want to enhance this
                    # based on your business logic (e.g., exclude holidays from HolidayCalander)
                    working_days = _calculate_working_days(period_from, period_to)
                    
                    # Calculate days present from attendance records
                    days_present = _calculate_days_present(employee, period_from, period_to)
                    
                    # Calculate net amount (simplified - you may want to add deductions, allowances, etc.)
                    # Basic calculation: (monthly_salary / working_days) * days_present
                    if working_days > 0:
                        daily_rate = employee.monthly_salary / working_days
                        net_amount = daily_rate * days_present
                    else:
                        net_amount = 0
                    
                    # Round to 2 decimal places
                    net_amount = round(net_amount, 2)
                    
                    # Create payroll record
                    payroll = PayrollRecord.objects.create(
                        employee=employee,
                        payroll_status=PayrollRecord.PayrollStatus.PENDING,
                        period_from=period_from,
                        period_to=period_to,
                        working_days=working_days,
                        days_present=days_present,
                        net_amount=net_amount,
                        notes=f'Auto-generated payroll for {today.year}-{today.month:02d}',
                        created_by=system_user
                    )
                    
                    created_count += 1
                    logger.info(f"Created payroll record {payroll.id} for employee {employee.employee_code}")
                    
                except Exception as e:
                    logger.error(f"Error generating payroll for employee {employee.employee_code}: {str(e)}")
                    continue
        
        result = {
            'status': 'success',
            'date': str(today),
            'period_from': str(period_from),
            'period_to': str(period_to),
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'total_employees': employees.count()
        }
        
        # Notify owners when payroll is generated
        if created_count > 0:
            send_notification_to_owners(
                title="Monthly Payroll Generated",
                message=f"Monthly payroll records have been generated for {created_count} employee(s) for {today.year}-{today.month:02d}",
                notification_type="Payroll",
                created_by=system_user
            )
        
        logger.info(f"Monthly payroll generation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_monthly_payroll task: {str(e)}", exc_info=True)
        raise


def _calculate_working_days(period_from, period_to):
    """
    Calculate working days between period_from and period_to.
    Excludes weekends (Saturday and Sunday).
    
    Args:
        period_from: Start date
        period_to: End date
    
    Returns:
        int: Number of working days
    """
    working_days = 0
    current_date = period_from
    
    while current_date <= period_to:
        # Check if it's not a weekend (Monday=0, Sunday=6)
        if current_date.weekday() < 5:  # Monday to Friday
            working_days += 1
        current_date += timedelta(days=1)
    
    return working_days


def _calculate_days_present(employee, period_from, period_to):
    """
    Calculate days present for an employee based on attendance records.
    
    Args:
        employee: Employee instance
        period_from: Start date
        period_to: End date
    
    Returns:
        int: Number of days present
    """
    from HR.models import Attendance
    
    # Count attendance records with status "Present" or "Half-Day"
    days_present = Attendance.objects.filter(
        employee=employee,
        attendance_date__gte=period_from,
        attendance_date__lte=period_to,
        attendance_status__in=[Attendance.AttendanceStatus.PRESENT, Attendance.AttendanceStatus.HALF_DAY]
    ).count()
    
    return days_present


@shared_task(bind=True, name='Scheduler.tasks.generate_amc_billing')
def generate_amc_billing(self):
    """
    Generate AMC billing records automatically based on billing cycle.
    
    This task runs daily and checks for AMCs that need new billing records generated.
    
    The task:
    1. Finds all active AMCs
    2. Calculates billing periods based on billing cycle (Monthly, Quarterly, Half-yearly, Yearly)
    3. Generates billing records for periods that haven't been generated yet
    4. Notifies all admins/superadmins when new bills are generated
    5. Ensures idempotency (doesn't create duplicate billing records)
    """
    try:
        # Get current date in Asia/Kolkata timezone
        from django.utils import timezone as tz
        import pytz
        
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        now = tz.now().astimezone(kolkata_tz)
        today = now.date()
        
        logger.info(f"Starting AMC billing generation for {today}")
        
        # Get system user for created_by field
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            logger.warning("No superuser found. Billing records will have null created_by.")
        
        # Get all active AMCs
        active_amcs = AMC.objects.filter(status=AMC.Status.ACTIVE)
        
        if not active_amcs.exists():
            logger.info("No active AMCs found. Skipping billing generation.")
            return {
                'status': 'skipped',
                'reason': 'No active AMCs found',
                'date': str(today)
            }
        
        total_bills_created = 0
        total_notifications_sent = 0
        amcs_processed = []
        
        with transaction.atomic():
            for amc in active_amcs:
                try:
                    # Check if AMC is still valid (end_date hasn't passed)
                    if amc.end_date < today:
                        logger.info(f"AMC {amc.amc_number} has expired (end_date: {amc.end_date}). Skipping.")
                        continue
                    
                    # Calculate billing periods and amounts
                    billing_periods = _calculate_billing_periods(amc, today)
                    
                    if not billing_periods:
                        logger.info(f"No billing periods to generate for AMC {amc.amc_number}")
                        continue
                    
                    bills_created_for_amc = 0
                    
                    for period in billing_periods:
                        period_from = period['period_from']
                        period_to = period['period_to']
                        amount = period['amount']
                        
                        # Check if billing record already exists for this period
                        existing_billing = AMCBilling.objects.filter(
                            amc=amc,
                            period_from=period_from,
                            period_to=period_to
                        ).first()
                        
                        if existing_billing:
                            logger.info(f"Billing record already exists for AMC {amc.amc_number} "
                                      f"period {period_from} to {period_to}. Skipping.")
                            continue
                        
                        # Generate bill number
                        bill_number = _generate_bill_number(amc, period_from)
                        
                        # Create billing record
                        billing = AMCBilling.objects.create(
                            amc=amc,
                            bill_number=bill_number,
                            bill_date=today,
                            period_from=period_from,
                            period_to=period_to,
                            amount=amount,
                            paid=False,
                            created_by=system_user
                        )
                        
                        bills_created_for_amc += 1
                        total_bills_created += 1
                        
                        logger.info(f"Created billing record {billing.bill_number} for AMC {amc.amc_number} "
                                  f"period {period_from} to {period_to}, amount: {amount}")
                    
                    if bills_created_for_amc > 0:
                        amcs_processed.append({
                            'amc_number': amc.amc_number,
                            'client_name': _get_client_name(amc.client),
                            'bills_created': bills_created_for_amc
                        })
                
                except Exception as e:
                    logger.error(f"Error processing AMC {amc.amc_number}: {str(e)}", exc_info=True)
                    continue
            
            # Send notifications to all superadmins (owners) if bills were created
            if total_bills_created > 0:
                admins = User.objects.filter(is_superuser=True).distinct()
                
                notification_count = 0
                for admin in admins:
                    try:
                        notification_title = f"New AMC Billing Records Generated"
                        notification_message = (
                            f"{total_bills_created} new AMC billing record(s) have been generated automatically.\n\n"
                            f"AMCs processed:\n"
                        )
                        
                        for amc_info in amcs_processed:
                            notification_message += (
                                f"- AMC {amc_info['amc_number']} ({amc_info['client_name']}): "
                                f"{amc_info['bills_created']} bill(s)\n"
                            )
                        
                        Notification.objects.create(
                            recipient=admin,
                            title=notification_title,
                            message=notification_message,
                            type=Notification.Type.AMC,
                            channel=Notification.Channel.IN_APP,
                            created_by=system_user
                        )
                        notification_count += 1
                    except Exception as e:
                        logger.error(f"Error creating notification for admin {admin.username}: {str(e)}")
                        continue
                
                total_notifications_sent = notification_count
                logger.info(f"Sent {total_notifications_sent} notifications to superadmins (owners) about new billing records")
        
        result = {
            'status': 'success',
            'date': str(today),
            'total_bills_created': total_bills_created,
            'total_notifications_sent': total_notifications_sent,
            'amcs_processed': amcs_processed
        }
        
        logger.info(f"AMC billing generation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_amc_billing task: {str(e)}", exc_info=True)
        raise


def _calculate_billing_periods(amc, today):
    """
    Calculate billing periods for an AMC that need to be generated.
    
    Args:
        amc: AMC instance
        today: Current date
    
    Returns:
        list: List of dictionaries with period_from, period_to, and amount
    """
    try:
        from dateutil.relativedelta import relativedelta
        USE_RELATIVEDELTA = True
    except ImportError:
        USE_RELATIVEDELTA = False
    
    periods = []
    
    # Calculate number of billing periods per year based on billing cycle
    billing_cycle_periods = {
        AMC.BillingCycle.MONTHLY: 12,
        AMC.BillingCycle.QUARTERLY: 4,
        AMC.BillingCycle.HALF_YEARLY: 2,
        AMC.BillingCycle.YEARLY: 1,
    }
    
    periods_per_year = billing_cycle_periods.get(amc.billing_cycle, 4)
    
    # Calculate total number of periods in the contract
    # Example: 1 Jan 2025 to 31 Dec 2025 = 1 year, quarterly = 4 periods
    contract_duration_days = (amc.end_date - amc.start_date).days + 1
    contract_duration_years = contract_duration_days / 365.25
    total_periods = int(periods_per_year * contract_duration_years)
    
    # Ensure at least 1 period
    if total_periods == 0:
        total_periods = 1
    
    # Calculate amount per period (divide total amount by number of periods)
    # Example: Rs 500 / 4 periods = Rs 125 per period
    amount_per_period = amc.amount / total_periods
    amount_per_period = round(amount_per_period, 2)
    
    # Calculate period duration in months for date calculations
    period_months = {
        AMC.BillingCycle.MONTHLY: 1,
        AMC.BillingCycle.QUARTERLY: 3,
        AMC.BillingCycle.HALF_YEARLY: 6,
        AMC.BillingCycle.YEARLY: 12,
    }
    
    months_per_period = period_months.get(amc.billing_cycle, 3)
    
    # Generate periods from start_date to end_date
    current_period_start = amc.start_date
    
    while current_period_start <= amc.end_date:
        # Calculate period end date using relativedelta for accurate month/year calculations
        if USE_RELATIVEDELTA:
            period_end = current_period_start + relativedelta(months=months_per_period) - timedelta(days=1)
        else:
            # Fallback if dateutil is not available
            if amc.billing_cycle == AMC.BillingCycle.MONTHLY:
                if current_period_start.month == 12:
                    period_end = date(current_period_start.year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(current_period_start.year, current_period_start.month + 1, 1) - timedelta(days=1)
            elif amc.billing_cycle == AMC.BillingCycle.QUARTERLY:
                month = current_period_start.month + 3
                year = current_period_start.year
                if month > 12:
                    month -= 12
                    year += 1
                period_end = date(year, month, 1) - timedelta(days=1)
            elif amc.billing_cycle == AMC.BillingCycle.HALF_YEARLY:
                month = current_period_start.month + 6
                year = current_period_start.year
                if month > 12:
                    month -= 12
                    year += 1
                period_end = date(year, month, 1) - timedelta(days=1)
            else:  # YEARLY
                period_end = date(current_period_start.year + 1, current_period_start.month, current_period_start.day) - timedelta(days=1)
        
        # Ensure period_end doesn't exceed AMC end_date
        if period_end > amc.end_date:
            period_end = amc.end_date
        
        # Only generate if period end date has passed (period_end <= today)
        # This means the billing period has completed and bill should be generated
        if period_end <= today:
            # Check if this period's billing record already exists
            existing = AMCBilling.objects.filter(
                amc=amc,
                period_from=current_period_start,
                period_to=period_end
            ).exists()
            
            if not existing:
                periods.append({
                    'period_from': current_period_start,
                    'period_to': period_end,
                    'amount': amount_per_period
                })
        
        # Move to next period (start from day after period_end)
        current_period_start = period_end + timedelta(days=1)
    
    return periods


def _generate_bill_number(amc, period_from):
    """
    Generate a unique bill number for an AMC billing record.
    
    Format: AMC-{amc_number}-{YYYY}-{MM}-{period_number}
    """
    # Get the billing cycle to determine period number
    if amc.billing_cycle == AMC.BillingCycle.MONTHLY:
        period_number = period_from.month
    elif amc.billing_cycle == AMC.BillingCycle.QUARTERLY:
        # Calculate quarter number (1-4)
        period_number = ((period_from.month - 1) // 3) + 1
    elif amc.billing_cycle == AMC.BillingCycle.HALF_YEARLY:
        # Calculate half-year number (1-2)
        period_number = ((period_from.month - 1) // 6) + 1
    else:  # YEARLY
        period_number = 1
    
    bill_number = f"AMC-{amc.amc_number}-{period_from.year}-{period_from.month:02d}-{period_number}"
    
    # Ensure uniqueness by appending a counter if needed
    counter = 1
    base_bill_number = bill_number
    while AMCBilling.objects.filter(bill_number=bill_number).exists():
        bill_number = f"{base_bill_number}-{counter}"
        counter += 1
    
    return bill_number


def _get_client_name(client):
    """Get client name for notification"""
    # Use the full_name property which gets name from profile.user
    full_name = client.full_name
    return full_name if full_name else f"Client {client.id}"


@shared_task(bind=True, name='Scheduler.tasks.send_scheduled_notification')
def send_scheduled_notification(self, title, message, notification_type, channel, created_by_id=None):
    """
    Send a scheduled notification to all employees at the scheduled time.
    
    This task is scheduled for a specific date/time and marks existing scheduled
    notifications as sent when that time arrives.
    
    Args:
        title: Notification title
        message: Notification message
        notification_type: Notification type (from Notification.Type)
        channel: Notification channel (from Notification.Channel)
        created_by_id: ID of the user who created the notification (optional)
    """
    try:
        from django.utils import timezone as tz
        from django.contrib.auth.models import User
        from Notifications.models import Notification
        from HR.models import Employee
        
        now = tz.now()
        
        # Get the user who created the notification
        created_by = None
        if created_by_id:
            try:
                created_by = User.objects.get(id=created_by_id)
            except User.DoesNotExist:
                logger.warning(f"User {created_by_id} not found for scheduled notification")
        
        # Find existing scheduled notifications that match this title, message, type, and channel
        # and haven't been sent yet (sent_at is None)
        scheduled_notifications = Notification.objects.filter(
            title=title,
            message=message,
            type=notification_type,
            channel=channel,
            scheduled_at__isnull=False,
            sent_at__isnull=True,
            created_by_id=created_by_id if created_by_id else None
        )
        
        notifications_sent = 0
        errors = []
        
        # Mark all matching scheduled notifications as sent
        for notification in scheduled_notifications:
            try:
                notification.sent_at = now
                notification.scheduled_at = None  # Clear scheduled_at since it's being sent now
                notification.save()
                notifications_sent += 1
                logger.info(f"Marked scheduled notification {notification.id} as sent for {notification.recipient.username}")
            except Exception as e:
                error_msg = f"Error marking notification {notification.id} as sent: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        # If no scheduled notifications found, create new ones (fallback for old scheduled tasks)
        if notifications_sent == 0:
            logger.warning(f"No scheduled notifications found matching criteria. Creating new notifications as fallback.")
            employees = Employee.objects.select_related('profile', 'profile__user').all()
            
            for employee in employees:
                if employee.profile and employee.profile.user:
                    user = employee.profile.user
                    try:
                        notification = Notification.objects.create(
                            recipient=user,
                            title=title,
                            message=message,
                            type=notification_type,
                            channel=channel,
                            scheduled_at=None,  # Not scheduled anymore, being sent now
                            sent_at=now,  # Mark as sent immediately
                            created_by=created_by
                        )
                        notifications_sent += 1
                        logger.info(f"Created and sent scheduled notification to {user.username} (fallback)")
                    except Exception as e:
                        error_msg = f"Error creating notification for {user.username}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg, exc_info=True)
        
        result = {
            'status': 'success',
            'notifications_sent': notifications_sent,
            'errors': errors if errors else None,
            'timestamp': str(now)
        }
        
        logger.info(f"Scheduled notification sent: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in send_scheduled_notification task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, name='Scheduler.tasks.send_scheduled_notifications')
def send_scheduled_notifications(self):
    """
    Send scheduled notifications that are due.
    
    This task runs periodically (every few minutes) to check for scheduled notifications
    that are due and sends them. This is a fallback for any notifications that were
    created with scheduled_at but not handled by the scheduled task.
    """
    try:
        from django.utils import timezone as tz
        import pytz
        
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        now = tz.now().astimezone(kolkata_tz)
        
        # Find notifications that are scheduled and due
        scheduled_notifications = Notification.objects.filter(
            scheduled_at__isnull=False,
            sent_at__isnull=True,
            scheduled_at__lte=now
        )
        
        sent_count = 0
        errors = []
        
        for notification in scheduled_notifications:
            try:
                notification.sent_at = now
                notification.scheduled_at = None  # Clear scheduled_at since it's being sent now
                notification.save()
                sent_count += 1
                logger.info(f"Sent scheduled notification {notification.id} to {notification.recipient.username}")
            except Exception as e:
                errors.append(f"Error sending notification {notification.id}: {str(e)}")
                logger.error(f"Error sending scheduled notification {notification.id}: {str(e)}")
        
        result = {
            'status': 'success',
            'sent_count': sent_count,
            'errors': errors if errors else None,
            'timestamp': str(now)
        }
        
        if sent_count > 0:
            logger.info(f"Scheduled notifications sent: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in send_scheduled_notifications task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, name='Scheduler.tasks.send_tender_emd_reminders')
def send_tender_emd_reminders(self):
    """
    Send reminders to owners about pending EMD collections.
    
    This task runs daily to check for tenders with pending EMD deposits
    and sends reminders to owners.
    """
    try:
        from django.utils import timezone as tz
        import pytz
        from datetime import timedelta
        
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        now = tz.now().astimezone(kolkata_tz)
        today = now.date()
        
        # Find tenders with pending EMD deposits (not refunded)
        pending_deposits = TenderDeposit.objects.filter(
            is_refunded=False,
            tender__status__in=[Tender.Status.FILED, Tender.Status.AWARDED]
        ).select_related('tender')
        
        if not pending_deposits.exists():
            logger.info("No pending EMD deposits found. Skipping reminders.")
            return {
                'status': 'skipped',
                'reason': 'No pending EMD deposits',
                'date': str(today)
            }
        
        # Group deposits by tender for better notification messages
        tender_deposits = {}
        for deposit in pending_deposits:
            tender_id = deposit.tender.id
            if tender_id not in tender_deposits:
                tender_deposits[tender_id] = {
                    'tender': deposit.tender,
                    'deposits': []
                }
            tender_deposits[tender_id]['deposits'].append(deposit)
        
        # Get system user for created_by field
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            logger.warning("No superuser found. Notifications will have null created_by.")
        
        reminder_count = 0
        total_amount = 0
        
        for tender_id, tender_data in tender_deposits.items():
            tender = tender_data['tender']
            deposits = tender_data['deposits']
            
            # Calculate total amount for this tender
            tender_total = sum(deposit.dd_amount for deposit in deposits)
            total_amount += tender_total
            
            # Create notification message
            deposit_count = len(deposits)
            deposit_list = "\n".join([
                f"- {deposit.deposit_type} (DD No: {deposit.dd_number}, Amount: ₹{deposit.dd_amount})"
                for deposit in deposits
            ])
            
            notification_title = f"Tender EMD Collection Reminder: {tender.name}"
            notification_message = (
                f"Reminder: {tender.name} has {deposit_count} pending EMD deposit(s) that need to be collected.\n\n"
                f"Pending Deposits:\n{deposit_list}\n\n"
                f"Total Amount: ₹{tender_total}\n\n"
                f"Please collect the EMD deposits at the earliest."
            )
            
            # Send notification to all owners
            try:
                send_notification_to_owners(
                    title=notification_title,
                    message=notification_message,
                    notification_type="Tender",
                    created_by=system_user
                )
                reminder_count += 1
                logger.info(f"Sent EMD reminder for tender {tender.name} (ID: {tender_id})")
            except Exception as e:
                logger.error(f"Error sending EMD reminder for tender {tender.name}: {str(e)}")
        
        result = {
            'status': 'success',
            'date': str(today),
            'reminders_sent': reminder_count,
            'tenders_with_pending_emds': len(tender_deposits),
            'total_pending_amount': float(total_amount)
        }
        
        logger.info(f"Tender EMD reminders sent: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in send_tender_emd_reminders task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, name='Scheduler.tasks.auto_close_awarded_tenders')
def auto_close_awarded_tenders(self):
    """
    Automatically close tenders with status 'Awarded' after their end_date has passed.
    
    This task runs daily and checks for tenders that:
    1. Have status 'Awarded'
    2. Have an end_date that has passed (end_date < today)
    
    These tenders will be automatically marked as 'Closed'.
    """
    try:
        from django.utils import timezone as tz
        import pytz
        
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        now = tz.now().astimezone(kolkata_tz)
        today = now.date()
        
        logger.info(f"Starting auto-close awarded tenders task for {today}")
        
        # Find tenders with status 'Awarded' and end_date < today
        tenders_to_close = Tender.objects.filter(
            status=Tender.Status.AWARDED,
            end_date__lt=today
        )
        
        if not tenders_to_close.exists():
            logger.info("No awarded tenders found that need to be closed.")
            return {
                'status': 'skipped',
                'reason': 'No tenders to close',
                'date': str(today)
            }
        
        closed_count = 0
        errors = []
        
        for tender in tenders_to_close:
            try:
                tender.status = Tender.Status.CLOSED
                tender.save()
                closed_count += 1
                logger.info(f"Auto-closed tender {tender.name} (ID: {tender.id}) - end_date was {tender.end_date}")
            except Exception as e:
                error_msg = f"Error closing tender {tender.name} (ID: {tender.id}): {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        result = {
            'status': 'success',
            'date': str(today),
            'closed_count': closed_count,
            'errors': errors if errors else None
        }
        
        logger.info(f"Auto-close awarded tenders completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in auto_close_awarded_tenders task: {str(e)}", exc_info=True)
        raise


@shared_task(bind=True, name='Scheduler.tasks.send_scheduled_email')
def send_scheduled_email(self, template_id, recipients, placeholder_values=None):
    """
    Send a scheduled email using an email template.
    
    Args:
        template_id: ID of the EmailTemplate
        recipients: List of email addresses
        placeholder_values: Dictionary of placeholder values to replace in the email body
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        from Notifications.models import EmailTemplate
        from django.utils import timezone as tz
        
        # Get the email template
        try:
            template = EmailTemplate.objects.get(id=template_id)
        except EmailTemplate.DoesNotExist:
            logger.error(f"Email template {template_id} not found")
            return {
                'status': 'error',
                'error': f'Email template {template_id} not found'
            }
        
        # Replace placeholders in subject and body
        subject = template.subject
        body = template.body
        
        if placeholder_values:
            for key, value in placeholder_values.items():
                placeholder = f"{{{{{key}}}}}"
                subject = subject.replace(placeholder, str(value))
                body = body.replace(placeholder, str(value))
        
        # Send email to all recipients
        email_sent_count = 0
        errors = []
        
        for recipient_email in recipients:
            try:
                send_mail(
                    subject=subject,
                    message=body,  # Plain text fallback
                    from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
                    recipient_list=[recipient_email],
                    html_message=body,  # HTML content
                    fail_silently=False,
                )
                email_sent_count += 1
                logger.info(f"Sent scheduled email to {recipient_email} using template {template.name}")
            except Exception as e:
                error_msg = f"Error sending email to {recipient_email}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        result = {
            'status': 'success',
            'template_id': template_id,
            'template_name': template.name,
            'recipients_count': len(recipients),
            'sent_count': email_sent_count,
            'errors': errors if errors else None,
            'timestamp': str(tz.now())
        }
        
        logger.info(f"Scheduled email sent: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in send_scheduled_email task: {str(e)}", exc_info=True)
        raise

