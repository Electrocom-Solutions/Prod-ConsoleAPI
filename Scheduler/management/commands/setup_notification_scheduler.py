"""
Management command to set up the scheduled notifications periodic task.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Command(BaseCommand):
    help = 'Set up the scheduled notifications periodic task (runs every 5 minutes to check for due notifications)'

    def handle(self, *args, **options):
        # Create or get the interval schedule for every 5 minutes
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created interval schedule: Every 5 minutes'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Using existing interval schedule: Every 5 minutes'))
        
        # Create or get the periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Send Scheduled Notifications',
            defaults={
                'task': 'Scheduler.tasks.send_scheduled_notifications',
                'interval': schedule,
                'enabled': True,
                'description': 'Check for scheduled notifications that are due and send them. Runs every 5 minutes.'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created periodic task: Send Scheduled Notifications'))
        else:
            # Update the task to ensure it's enabled and using the correct schedule
            task.interval = schedule
            task.enabled = True
            task.description = 'Check for scheduled notifications that are due and send them. Runs every 5 minutes.'
            task.save()
            self.stdout.write(self.style.SUCCESS(f'Updated periodic task: Send Scheduled Notifications'))
        
        self.stdout.write(self.style.SUCCESS('Scheduled notifications periodic task is set up successfully!'))

