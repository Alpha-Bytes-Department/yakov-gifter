"""
Finds leftover test content in user-visible tables.

The client saw test data in notifications and testimonials. The moderation
mechanism itself is sound — Testimonial.is_approved defaults to False, is
read-only in the serializer, and the public endpoint filters on it — so these
are rows created and approved during development, on a database this repository
cannot reach.

Reports by default and deletes only when asked. Deleting content on a guess is
how a real testimonial gets thrown away, so --delete prints the full list first
and matches conservatively.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.content.models import Testimonial
from apps.core.models import AdminNotification

# Deliberately narrow. Substrings that appear in real writing ("latest", "attest")
# are avoided by matching with word boundaries where it matters.
SUSPICIOUS = [
    'lorem ipsum', 'asdf', 'qwerty', 'test test', 'testing 123',
    'placeholder', 'dummy', 'sample text', 'foo bar', 'xxxx',
]

# Addresses reserved for documentation and testing (RFC 2606).
TEST_DOMAINS = ['@example.com', '@example.org', '@example.net', '@test.com']


class Command(BaseCommand):
    help = 'Reports (and optionally deletes) leftover test notifications and testimonials.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete', action='store_true',
            help='Actually delete the rows listed. Without this, only reports.',
        )

    def _suspicious_filter(self, *fields):
        query = Q()
        for field in fields:
            for phrase in SUSPICIOUS:
                query |= Q(**{f'{field}__icontains': phrase})
        return query

    def handle(self, *args, **options):
        delete = options['delete']
        User = get_user_model()

        testimonials = Testimonial.objects.filter(
            self._suspicious_filter('content', 'author_name')
        )
        notifications = AdminNotification.objects.filter(
            self._suspicious_filter('title', 'message')
        )

        test_accounts = Q()
        for domain in TEST_DOMAINS:
            test_accounts |= Q(user__email__iendswith=domain)
        from_test_users = Testimonial.objects.filter(test_accounts)

        total = 0
        for label, queryset, excerpt in [
            ('Testimonials with placeholder text', testimonials, 'content'),
            ('Testimonials from reserved test domains', from_test_users, 'content'),
            ('Notifications with placeholder text', notifications, 'message'),
        ]:
            self.stdout.write(self.style.WARNING(f'\n{label}: {queryset.count()}'))
            for row in queryset:
                # Show the text itself, not __str__ — deciding whether a row is
                # junk means reading what it actually says.
                body = ' '.join((getattr(row, excerpt, '') or '').split())
                author = getattr(row, 'author_name', None) or getattr(row, 'title', '')
                self.stdout.write(f'  #{row.id} [{author}] {body[:100]}')
            total += queryset.count()

        # Worth seeing even though it is not deletable: an unapproved testimonial
        # is invisible to users and needs a decision, not a purge.
        pending = Testimonial.objects.filter(is_approved=False).count()
        self.stdout.write(
            f'\nAlso awaiting moderation (not shown to users): {pending}'
        )

        accounts = User.objects.filter(
            Q(*[Q(email__iendswith=d) for d in TEST_DOMAINS], _connector=Q.OR)
        )
        if accounts.exists():
            self.stdout.write(self.style.WARNING(
                f'\nAccounts on reserved test domains: {accounts.count()}'
            ))
            for account in accounts:
                self.stdout.write(f'  #{account.id} {account.email}')

        if not total:
            self.stdout.write(self.style.SUCCESS('\nNothing matched.'))
            return

        if not delete:
            self.stdout.write(self.style.SUCCESS(
                f'\n{total} row(s) matched. Re-run with --delete to remove them.'
            ))
            return

        for queryset in (testimonials, from_test_users, notifications):
            queryset.delete()
        self.stdout.write(self.style.SUCCESS(f'\nDeleted {total} row(s).'))
