"""
Management command to set up the absent marking periodic task.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up the absent marking periodic task (runs daily at 11:40 PM Asia/Kolkata, except Sunday)'

    def handle(self, *args, **options):
        # Create or get the crontab schedule for 11:40 PM daily (23:40)
        # crontab format: minute, hour, day_of_month, month_of_year, day_of_week
        # day_of_week: 0=Monday, 6=Sunday
        # We use 0-5 to exclude Sunday (6)
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute='40',
            hour='23',
            day_of_week='0,1,2,3,4,5',  # Monday to Saturday (exclude Sunday)
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata'
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created crontab schedule: Daily at 11:40 PM (Asia/Kolkata), Monday-Saturday'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing crontab schedule: Daily at 11:40 PM (Asia/Kolkata), Monday-Saturday'))
        
        # Create or get the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Mark Absent Employees',
            defaults={
                'task': 'Scheduler.tasks.mark_absent_employees',
                'crontab': schedule,
                'enabled': True,
                'description': 'Mark employees as absent who didn\'t mark attendance for the day. Runs daily at 11:40 PM (Asia/Kolkata), Monday-Saturday.'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created periodic task: {task.name}'))
        else:
            # Update existing task to ensure it's enabled and has correct schedule
            task.crontab = schedule
            task.enabled = True
            task.description = 'Mark employees as absent who didn\'t mark attendance for the day. Runs daily at 11:40 PM (Asia/Kolkata), Monday-Saturday.'
            task.save()
            self.stdout.write(self.style.SUCCESS(f'Updated periodic task: {task.name}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nPeriodic task setup complete!\n'
            f'Task: {task.name}\n'
            f'Schedule: Daily at 11:40 PM (Asia/Kolkata), Monday-Saturday\n'
            f'Task will run: {task.task}\n'
            f'Task will mark employees as absent if they didn\'t mark attendance.\n'
            f'\nTo start the Celery Beat scheduler, run:\n'
            f'celery -A API beat -l info'
        ))

