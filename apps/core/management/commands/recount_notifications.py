"""
Repairs stored recipient counts on existing notifications.

The dashboard was showing 50 and 100 recipients on an install with five users.
recipients_count is a snapshot written when a notification is created; rows that
predate the correct logic, or were entered by hand in the Django admin, kept
whatever number they were given. This recomputes them from the real audience.
"""
from django.core.management.base import BaseCommand

from apps.core.models import AdminNotification


class Command(BaseCommand):
    help = 'Recomputes recipients_count on every AdminNotification.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        changed = unchanged = 0

        for notification in AdminNotification.objects.all():
            before = notification.recipients_count
            after = notification.audience_queryset().count()

            if before == after:
                unchanged += 1
                continue

            self.stdout.write(
                f'  #{notification.id} "{notification.title[:40]}" '
                f'({notification.audience}): {before} -> {after}'
            )
            if not dry_run:
                notification.recount_recipients()
            changed += 1

        prefix = 'Would correct' if dry_run else 'Corrected'
        self.stdout.write(self.style.SUCCESS(
            f'{prefix} {changed}; {unchanged} already correct.'
        ))
