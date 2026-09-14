"""
Builds the weekly ReadingSchedule from the Hebrew calendar.

The schedule in production had Bereishis falling in August. The cause was in
seed_parshas, which assigned `Parsha.objects.first()` to the coming Shabbos —
and since Parsha is ordered by id, "first" is always Bereishis regardless of the
date. This computes the real reading instead, using pyluach (the same algorithm
Hebcal implements).
"""
import datetime

from django.core.management.base import BaseCommand, CommandError
from pyluach import dates, parshios

from apps.parshas.models import Parsha, ReadingSchedule


# pyluach's spellings, paired with the names this project seeds into the Parsha
# table. The two lists disagree constantly (Bereishis/Bereishis, Toldos/Toldot,
# Ki Sisa/Ki Tisa, Mattos/Matot), so matching on the raw strings silently fails.
# Both are in the standard order, so index i is the same portion in each.
DB_NAMES = [
    'Bereishis', 'Noach', 'Lech-Lecha', 'Vayera', 'Chayei Sarah', 'Toldot',
    'Vayetzei', 'Vayishlach', 'Vayeshev', 'Miketz', 'Vayigash', 'Vayechi',
    'Shemot', "Va'era", 'Bo', 'Beshalach', 'Yitro', 'Mishpatim', 'Terumah',
    'Tetzaveh', 'Ki Tisa', 'Vayakhel', 'Pekudei', 'Vayikra', 'Tzav', 'Shemini',
    'Tazria', 'Metzora', 'Acharei Mot', 'Kedoshim', 'Emor', 'Behar',
    'Bechukotai', 'Bamidbar', 'Nasso', "Beha'alotcha", "Sh'lach", 'Korach',
    'Chukat', 'Balak', 'Pinchas', 'Matot', 'Masei', 'Devarim', "Va'etchanan",
    'Eikev', "Re'eh", 'Shoftim', 'Ki Teitzei', 'Ki Tavo', 'Nitzavim',
    'Vayeilech', "Ha'azinu", "V'Zot HaBerachah",
]


def normalize(name):
    """Folds a name to a comparison key: lowercase, letters only."""
    return ''.join(ch for ch in (name or '').lower() if ch.isalpha())


def build_lookup():
    """
    Maps a pyluach parsha index to the matching Parsha row.

    Tries the project's own spelling first, then pyluach's, then the ordinal
    position as a last resort. Anything still unmatched is reported rather than
    skipped quietly — a gap in the schedule is exactly the class of bug this
    command exists to fix.
    """
    by_name = {normalize(p.name): p for p in Parsha.objects.all()}
    ordered = list(Parsha.objects.order_by('id'))

    lookup, missing = {}, []
    for index, pyluach_name in enumerate(parshios.PARSHIOS):
        candidates = [pyluach_name]
        if index < len(DB_NAMES):
            candidates.insert(0, DB_NAMES[index])

        match = next(
            (by_name[normalize(c)] for c in candidates if normalize(c) in by_name),
            None,
        )
        if match is None and index < len(ordered):
            match = ordered[index]

        if match is None:
            missing.append(pyluach_name)
        else:
            lookup[index] = match

    return lookup, missing


class Command(BaseCommand):
    help = 'Generates the weekly Torah reading schedule from the Hebrew calendar.'

    def add_arguments(self, parser):
        parser.add_argument('--start', help='YYYY-MM-DD (default: today)')
        parser.add_argument(
            '--years', type=int, default=3,
            help='How many years forward to generate (default: 3)',
        )
        parser.add_argument(
            '--israel', action='store_true',
            help='Use the Israeli reading cycle instead of the diaspora one.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing.',
        )

    def handle(self, *args, **options):
        if Parsha.objects.count() == 0:
            raise CommandError('No Parsha rows. Run seed_parshas first.')

        start = (
            datetime.date.fromisoformat(options['start'])
            if options['start'] else datetime.date.today()
        )
        end = start + datetime.timedelta(days=365 * options['years'])
        israel = options['israel']
        dry_run = options['dry_run']

        lookup, missing = build_lookup()
        if missing:
            self.stdout.write(self.style.WARNING(
                f'No Parsha row matched: {", ".join(missing)}'
            ))

        # Walk to the first Saturday on or after the start date.
        cursor = start + datetime.timedelta(days=(5 - start.weekday()) % 7)

        created = updated = unchanged = skipped = 0
        while cursor <= end:
            indices = parshios.getparsha(
                dates.GregorianDate.from_pydate(cursor), israel=israel
            )

            # None means a Yom Tov reading displaces the weekly portion.
            if not indices:
                skipped += 1
                cursor += datetime.timedelta(days=7)
                continue

            # A combined week (e.g. Mattos-Masei) yields two indices. The table
            # holds the 54 individual portions only, so anchor on the first.
            parsha = lookup.get(indices[0])
            if parsha is None:
                skipped += 1
                cursor += datetime.timedelta(days=7)
                continue

            hebrew_date = dates.GregorianDate.from_pydate(cursor).to_heb().hebrew_date_string()

            existing = ReadingSchedule.objects.filter(date=cursor).first()
            if existing is None:
                if not dry_run:
                    ReadingSchedule.objects.create(
                        date=cursor, parsha=parsha, hebrew_date=hebrew_date,
                    )
                created += 1
            elif existing.parsha_id != parsha.id or existing.hebrew_date != hebrew_date:
                if not dry_run:
                    existing.parsha = parsha
                    existing.hebrew_date = hebrew_date
                    existing.save(update_fields=['parsha', 'hebrew_date'])
                updated += 1
                self.stdout.write(
                    f'  {cursor}: {existing.parsha.name} -> {parsha.name}'
                )
            else:
                unchanged += 1

            cursor += datetime.timedelta(days=7)

        prefix = 'Would write' if dry_run else 'Wrote'
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}: {created} created, {updated} corrected, '
            f'{unchanged} already correct, {skipped} skipped (Yom Tov).'
        ))
