import datetime
from django.core.management.base import BaseCommand
from apps.parshas.models import Parsha, ReadingSchedule
from apps.content.models import AudioTrack

class Command(BaseCommand):
    help = 'Seeds all 54 Parshas across 5 Chumash books and creates published sample audio tracks'

    def handle(self, *args, **options):
        parshas_data = [
            # Bereishis (12)
            ("Bereishis", "בְּרֵאשִׁית", "Bereishis", "1:1 - 6:8", "Yeshayahu 42:5 - 43:10"),
            ("Noach", "נֹחַ", "Bereishis", "6:9 - 11:32", "Yeshayahu 54:1 - 55:5"),
            ("Lech-Lecha", "לֶךְ-לְךָ", "Bereishis", "12:1 - 17:27", "Yeshayahu 40:27 - 41:16"),
            ("Vayera", "וַיֵּרָא", "Bereishis", "18:1 - 22:24", "Melachim II 4:1 - 4:37"),
            ("Chayei Sarah", "חַיֵּי שָׂרָה", "Bereishis", "23:1 - 25:18", "Melachim I 1:1 - 1:31"),
            ("Toldot", "תּוֹלְדֹת", "Bereishis", "25:19 - 28:9", "Malachi 1:1 - 2:7"),
            ("Vayetzei", "וַיֵּצֵא", "Bereishis", "28:10 - 32:3", "Hoshea 12:13 - 14:10"),
            ("Vayishlach", "וַיִּשְׁלַח", "Bereishis", "32:4 - 36:43", "Ovadiah 1:1 - 1:21"),
            ("Vayeshev", "וַיֵּשֶׁב", "Bereishis", "37:1 - 40:23", "Amos 2:6 - 3:8"),
            ("Miketz", "מִקֵּץ", "Bereishis", "41:1 - 44:17", "Melachim I 3:15 - 4:1"),
            ("Vayigash", "וַיִּגַּשׁ", "Bereishis", "44:18 - 47:27", "Yechezkel 37:15 - 37:28"),
            ("Vayechi", "וַיְחִי", "Bereishis", "47:28 - 50:26", "Melachim I 2:1 - 2:12"),
            
            # Shemot (11)
            ("Shemot", "שְׁמוֹת", "Shemot", "1:1 - 6:1", "Yeshayahu 27:6 - 28:13"),
            ("Va'era", "וָאֵרָא", "Shemot", "6:2 - 9:35", "Yechezkel 28:25 - 29:21"),
            ("Bo", "בֹּא", "Shemot", "10:1 - 13:16", "Yirmiyahu 46:13 - 46:28"),
            ("Beshalach", "בְּשַׁלַּח", "Shemot", "13:17 - 17:16", "Shoftim 4:4 - 5:31"),
            ("Yitro", "יִתְרוֹ", "Shemot", "18:1 - 20:23", "Yeshayahu 6:1 - 7:6"),
            ("Mishpatim", "מִשְׁפָּטִים", "Shemot", "21:1 - 24:18", "Yirmiyahu 34:8 - 34:22"),
            ("Terumah", "תְּרוּמָה", "Shemot", "25:1 - 27:19", "Melachim I 5:26 - 6:13"),
            ("Tetzaveh", "תְּצַוֶּה", "Shemot", "27:20 - 30:10", "Yechezkel 43:10 - 43:27"),
            ("Ki Tisa", "כִּי תִשָּׂא", "Shemot", "30:11 - 34:35", "Melachim I 18:1 - 18:39"),
            ("Vayakhel", "וַיַּקְהֵל", "Shemot", "35:1 - 38:20", "Melachim I 7:40 - 7:50"),
            ("Pekudei", "פְּקוּדֵי", "Shemot", "38:21 - 40:38", "Melachim I 7:51 - 8:21"),

            # Vayikra (10)
            ("Vayikra", "וַיִּקְרָא", "Vayikra", "1:1 - 5:26", "Yeshayahu 43:21 - 44:23"),
            ("Tzav", "צַו", "Vayikra", "6:1 - 8:36", "Yirmiyahu 7:21 - 8:3"),
            ("Shemini", "שְׁמִינִי", "Vayikra", "9:1 - 11:47", "Shmuel II 6:1 - 7:17"),
            ("Tazria", "תַּזְרִיעַ", "Vayikra", "12:1 - 13:59", "Melachim II 4:42 - 5:19"),
            ("Metzora", "מְצֹרָע", "Vayikra", "14:1 - 15:33", "Melachim II 7:3 - 7:20"),
            ("Acharei Mot", "אַחֲרֵי מוֹת", "Vayikra", "16:1 - 18:30", "Amos 9:7 - 9:15"),
            ("Kedoshim", "קְדֹשִׁים", "Vayikra", "19:1 - 20:27", "Yechezkel 22:1 - 22:19"),
            ("Emor", "אֱמֹר", "Vayikra", "21:1 - 24:23", "Yechezkel 44:15 - 44:31"),
            ("Behar", "בְּהַר", "Vayikra", "25:1 - 26:2", "Yirmiyahu 32:6 - 32:27"),
            ("Bechukotai", "בְּחֻקֹּתַי", "Vayikra", "26:3 - 27:34", "Yirmiyahu 16:19 - 17:14"),

            # Bamidbar (10)
            ("Bamidbar", "בְּמִדְבַּר", "Bamidbar", "1:1 - 4:20", "Hoshea 2:1 - 2:22"),
            ("Nasso", "נָשֹׂא", "Bamidbar", "4:21 - 7:89", "Shoftim 13:2 - 13:25"),
            ("Beha'alotcha", "בְּהַעֲלֹתְךָ", "Bamidbar", "8:1 - 12:16", "Zechariah 2:14 - 4:7"),
            ("Sh'lach", "שְׁלַח-לְךָ", "Bamidbar", "13:1 - 15:41", "Yehoshua 2:1 - 2:24"),
            ("Korach", "קֹרַח", "Bamidbar", "16:1 - 18:32", "Shmuel I 11:14 - 12:22"),
            ("Chukat", "חֻקַּת", "Bamidbar", "19:1 - 22:1", "Shoftim 11:1 - 11:33"),
            ("Balak", "בָּלָק", "Bamidbar", "22:2 - 25:9", "Michah 5:6 - 6:8"),
            ("Pinchas", "פִּינְחָס", "Bamidbar", "25:10 - 30:1", "Melachim I 18:46 - 19:21"),
            ("Matot", "מַטּוֹת", "Bamidbar", "30:2 - 32:42", "Yirmiyahu 1:1 - 2:3"),
            ("Masei", "מַסְעֵי", "Bamidbar", "33:1 - 36:13", "Yirmiyahu 2:4 - 2:28"),

            # Devarim (11)
            ("Devarim", "דְּבָרִים", "Devarim", "1:1 - 3:22", "Yeshayahu 1:1 - 1:27"),
            ("Va'etchanan", "וָאֶתְחַנַּן", "Devarim", "3:23 - 7:11", "Yeshayahu 40:1 - 40:26"),
            ("Eikev", "עֵקֶב", "Devarim", "7:12 - 11:25", "Yeshayahu 49:14 - 51:3"),
            ("Re'eh", "רְאֵה", "Devarim", "11:26 - 16:17", "Yeshayahu 54:11 - 55:5"),
            ("Shoftim", "שֹׁפְטִים", "Devarim", "16:18 - 21:9", "Yeshayahu 51:12 - 52:12"),
            ("Ki Teitzei", "כִּי-תֵצֵא", "Devarim", "21:10 - 25:19", "Yeshayahu 54:1 - 54:10"),
            ("Ki Tavo", "כִּי-תָבוֹא", "Devarim", "26:1 - 29:8", "Yeshayahu 60:1 - 60:22"),
            ("Nitzavim", "נִצָּבִים", "Devarim", "29:9 - 30:20", "Yeshayahu 61:10 - 63:9"),
            ("Vayeilech", "וַיֵּלֶךְ", "Devarim", "31:1 - 31:30", "Yeshayahu 55:6 - 56:8"),
            ("Ha'azinu", "הַאֲזִינוּ", "Devarim", "32:1 - 32:52", "Shmuel II 22:1 - 22:51"),
            ("V'Zot HaBerachah", "וְזֹאת הַבְּרָכָה", "Devarim", "33:1 - 34:12", "Yehoshua 1:1 - 1:18")
        ]

        created_count = 0
        for name, heb, sefer, cv, haft in parshas_data:
            p, created = Parsha.objects.get_or_create(
                name=name,
                defaults={
                    'name_hebrew': heb,
                    'sefer': sefer,
                    'chapter_verse': cv,
                    'haftorah_info': haft
                }
            )
            if created:
                created_count += 1

            # Seed sample audio tracks for each parsha (Aliyos 1..7 + Haftorah)
            segments = [
                ('Aliya 1', 'chumash', 'free', 'aliya_1'),
                ('Aliya 2', 'chumash', 'free', 'aliya_2'),
                ('Aliya 3', 'chumash', 'pro', 'aliya_3'),
                ('Aliya 4', 'chumash', 'pro', 'aliya_4'),
                ('Aliya 5', 'chumash', 'pro', 'aliya_5'),
                ('Aliya 6', 'chumash', 'pro', 'aliya_6'),
                ('Aliya 7', 'chumash', 'pro', 'aliya_7'),
                ('Maftir', 'chumash', 'pro', 'maftir'),
                ('Haftorah', 'haftoros', 'pro', 'haftorah'),
            ]

            for label, cat, access, seg_code in segments:
                AudioTrack.objects.get_or_create(
                    parsha=p,
                    segment_type=seg_code,
                    defaults={
                        'title': f"{p.name} - {label}",
                        'category': cat,
                        'access_level': access,
                        'status': 'published',
                        'duration_seconds': 180,
                        'file_size_bytes': 2500000,
                        'grouping': label,
                    }
                )

        # The reading schedule is deliberately NOT seeded here any more. This
        # used to assign Parsha.objects.first() to the coming Shabbos — and
        # Parsha is ordered by id, so "first" is always Bereishis whatever the
        # date. That is how the live schedule came to show Bereishis in August.
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} new Parshas and tracks! Total Parshas: {Parsha.objects.count()}"))
        self.stdout.write(self.style.WARNING(
            'Next: run `manage.py seed_reading_schedule` to build the weekly '
            'schedule from the Hebrew calendar.'
        ))
