"""
Bar mitzvah date arithmetic.

Mirrors test/hebrew_date_utils_test.dart in the mobile app — if these two ever
disagree, a boy is shown one portion in the app and another by the API.
"""
import datetime

from django.test import TestCase
from pyluach import dates

from apps.parshas.hebrew_dates import hebrew_bar_mitzvah_date


class BarMitzvahDateTests(TestCase):
    def test_lands_on_the_thirteenth_hebrew_birthday(self):
        dob = datetime.date(2013, 6, 15)
        result = hebrew_bar_mitzvah_date(dob)

        birth = dates.GregorianDate.from_pydate(dob).to_heb()
        target = dates.GregorianDate.from_pydate(result).to_heb()

        self.assertEqual(target.year, birth.year + 13)
        self.assertEqual(target.month, birth.month)
        self.assertEqual(target.day, birth.day)

    def test_is_not_the_gregorian_answer(self):
        dob = datetime.date(2013, 6, 15)
        self.assertNotEqual(hebrew_bar_mitzvah_date(dob), datetime.date(2026, 6, 15))

    def test_adar_ii_birth_in_a_regular_thirteenth_year_falls_back_to_adar(self):
        # 5784 is a leap year; 5797 is not. This case used to raise ValueError
        # and get swallowed into a plain Gregorian +13.
        dob = dates.HebrewDate(5784, 13, 10).to_pydate()
        result = hebrew_bar_mitzvah_date(dob)
        target = dates.GregorianDate.from_pydate(result).to_heb()

        self.assertEqual(target.year, 5797)
        self.assertEqual(target.month, 12)

        naive = dob.replace(year=dob.year + 13)
        self.assertNotEqual(result, naive)

    def test_after_sunset_moves_to_the_next_hebrew_day(self):
        dob = datetime.date(2013, 6, 15)
        before = hebrew_bar_mitzvah_date(dob)
        after = hebrew_bar_mitzvah_date(dob, born_after_sunset=True)
        self.assertNotEqual(before, after)

    def test_never_raises_across_a_wide_sweep(self):
        dob = datetime.date(2008, 1, 1)
        for _ in range(400):
            with self.subTest(dob=dob):
                self.assertIsInstance(hebrew_bar_mitzvah_date(dob), datetime.date)
            dob += datetime.timedelta(days=7)
