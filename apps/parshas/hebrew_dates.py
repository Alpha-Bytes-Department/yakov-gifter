"""
Hebrew calendar helpers.

Mirrors the logic the mobile app uses (lib/utils/hebrew_date_utils.dart) so the
two never disagree about which portion a boy reads.
"""
import datetime

from pyluach import dates

ADAR = 12
ADAR_II = 13


def _is_leap(hebrew_year):
    """A Hebrew leap year carries a 13th month, Adar II."""
    return dates.HebrewDate._is_leap(hebrew_year) if hasattr(
        dates.HebrewDate, '_is_leap'
    ) else (((hebrew_year * 7) + 1) % 19) < 7


def hebrew_bar_mitzvah_date(date_of_birth, born_after_sunset=False):
    """
    The 13th *Hebrew* birthday for a Gregorian date of birth.

    Deliberately not `date_of_birth.year + 13`: the calendars drift by roughly
    -23 to +8 days over 13 years, which is more than enough to land in a
    different reading week and hand the boy the wrong parsha to learn.

    A Hebrew day starts at nightfall, so [born_after_sunset] moves the birth to
    the following Hebrew date — which can shift the portion by a full week.

    Adar follows common practice: a boy born in Adar II whose 13th year is not a
    leap year keeps Adar; one born in Adar of a regular year whose 13th year is a
    leap year observes it in Adar II. Getting this wrong used to throw, and the
    old `except` swallowed it into a plain Gregorian +13 — the exact answer the
    conversion exists to avoid.
    """
    if born_after_sunset:
        date_of_birth = date_of_birth + datetime.timedelta(days=1)

    birth = dates.GregorianDate.from_pydate(date_of_birth).to_heb()

    target_year = birth.year + 13
    month = birth.month
    target_is_leap = _is_leap(target_year)
    birth_is_leap = _is_leap(birth.year)

    if month == ADAR_II and not target_is_leap:
        month = ADAR
    elif month == ADAR and not birth_is_leap and target_is_leap:
        month = ADAR_II

    day = birth.day
    # A 30th only exists in a full month; fall back to the 29th rather than
    # raising, matching the app.
    while day > 0:
        try:
            return dates.HebrewDate(target_year, month, day).to_pydate()
        except ValueError:
            day -= 1

    raise ValueError(f'Could not resolve a bar mitzvah date for {date_of_birth}')
