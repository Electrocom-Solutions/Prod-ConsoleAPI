"""
Management command to set up the monthly payroll generation periodic task.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up the monthly payroll generation periodic task (runs daily at 11:00 PM Asia/Kolkata)'

    def handle(self, *args, **options):
        # Create or get the crontab schedule for 11:00 PM daily (23:00)
        # crontab format: minute, hour, day_of_month, month_of_year, day_of_week
        # * means every
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='23',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata'
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created crontab schedule: Daily at 11:00 PM (Asia/Kolkata)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing crontab schedule: Daily at 11:00 PM (Asia/Kolkata)'))
        
        # Create or get the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Generate Monthly Payroll',
            defaults={
                'task': 'Scheduler.tasks.generate_monthly_payroll',
                'crontab': schedule,
                'enabled': True,
                'description': 'Generate monthly payroll records for all employees on the last day of each month at 11:00 PM (Asia/Kolkata)'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created periodic task: {task.name}'))
        else:
            # Update existing task to ensure it's enabled and has correct schedule
            task.crontab = schedule
            task.enabled = True
            task.description = 'Generate monthly payroll records for all employees on the last day of each month at 11:00 PM (Asia/Kolkata)'
            task.save()
            self.stdout.write(self.style.SUCCESS(f'Updated periodic task: {task.name}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nPeriodic task setup complete!\n'
            f'Task: {task.name}\n'
            f'Schedule: Daily at 11:00 PM (Asia/Kolkata)\n'
            f'Task will run: {task.task}\n'
            f'Task will generate payroll records only on the last day of each month.\n'
            f'\nTo start the Celery Beat scheduler, run:\n'
            f'celery -A API beat -l info'
        ))

