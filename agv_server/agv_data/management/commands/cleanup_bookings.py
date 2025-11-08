"""
Django management command to clean up old completed bookings.
This helps prevent the Booking table from growing indefinitely.

Usage:
    python manage.py cleanup_bookings --days 1
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from agv_data.models import Booking


class Command(BaseCommand):
    help = 'Delete old completed booking records to prevent database bloat.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to keep bookings (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days_to_keep = options['days']
        dry_run = options['dry_run']
        
        cutoff_time = timezone.now() - timedelta(days=days_to_keep)
        
        self.stdout.write(
            self.style.WARNING(
                f"{'[DRY RUN] ' if dry_run else ''}Looking for bookings older than {cutoff_time}..."
            )
        )
        
        old_bookings = Booking.objects.filter(end_time__lt=cutoff_time)
        count = old_bookings.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("No old bookings found. Database is clean.")
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f"Found {count} old booking(s) to delete.")
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "[DRY RUN] No bookings were actually deleted. Remove --dry-run to perform the cleanup."
                )
            )
        else:
            deleted_count, _ = old_bookings.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} old booking(s)."
                )
            )
