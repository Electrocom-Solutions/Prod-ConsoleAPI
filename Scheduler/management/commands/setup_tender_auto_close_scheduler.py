"""
Management command to set up the tender auto-close periodic task.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json


class Command(BaseCommand):
    help = 'Set up the tender auto-close periodic task (runs daily at 1:00 AM Asia/Kolkata)'

    def handle(self, *args, **options):
        # Create or get the crontab schedule for 1:00 AM daily (01:00)
        # crontab format: minute, hour, day_of_month, month_of_year, day_of_week
        # * means every
        schedule, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='1',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Asia/Kolkata'
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created crontab schedule: Daily at 1:00 AM (Asia/Kolkata)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing crontab schedule: Daily at 1:00 AM (Asia/Kolkata)'))
        
        # Create or get the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Auto-Close Awarded Tenders',
            defaults={
                'task': 'Scheduler.tasks.auto_close_awarded_tenders',
                'crontab': schedule,
                'enabled': True,
                'description': 'Automatically close tenders with status "Awarded" after their end_date has passed. Runs daily at 1:00 AM (Asia/Kolkata).'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created periodic task: {task.name}'))
        else:
            # Update existing task to ensure it's enabled and has correct schedule
            task.crontab = schedule
            task.enabled = True
            task.description = 'Automatically close tenders with status "Awarded" after their end_date has passed. Runs daily at 1:00 AM (Asia/Kolkata).'
            task.save()
            self.stdout.write(self.style.SUCCESS(f'Updated periodic task: {task.name}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nPeriodic task setup complete!\n'
            f'Task: {task.name}\n'
            f'Schedule: Daily at 1:00 AM (Asia/Kolkata)\n'
            f'Task will run: {task.task}\n'
            f'Task will automatically close tenders with status "Awarded" if their end_date has passed.\n'
            f'\nTo start the Celery Beat scheduler, run:\n'
            f'celery -A API beat -l info'
        ))

