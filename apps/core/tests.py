"""
Regression tests for the dashboard access controls.

These cover the findings that the client's audit rated CRITICAL: dashboard pages
rendering without server-side authentication, and the Stripe webhook accepting
unsigned payloads.
"""
import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


DASHBOARD_PAGES = [
    'admin_dashboard_overview',
    'admin_dashboard_analytics',
    'admin_dashboard_audio',
    'admin_dashboard_payments',
    'admin_dashboard_notifications',
    'admin_dashboard_settings',
    'admin_dashboard_coaching',
    'admin_dashboard_schedule',
    'admin_dashboard_users',
    'admin_dashboard_feedback',
    'admin_dashboard_testimonials',
]


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.save()

        self.civilian = User.objects.create_user(
            email='civilian@example.com', password='correct-horse-battery',
            first_name='Civ', last_name='Ilian',
        )

    def test_anonymous_cannot_render_any_dashboard_page(self):
        for name in DASHBOARD_PAGES:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn('/dashboard/login/', response['Location'])

    def test_signed_in_non_staff_is_refused(self):
        self.client.force_login(self.civilian)
        for name in DASHBOARD_PAGES:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 403)

    def test_staff_can_render_dashboard(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin_dashboard_overview'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_stays_public(self):
        response = self.client.get(reverse('admin_dashboard_login'))
        self.assertEqual(response.status_code, 200)
        # Needs to hand out a CSRF cookie for the sign-in POST.
        self.assertIn('csrftoken', response.cookies)


class DashboardSessionLoginTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.save()
        self.url = reverse('admin_dashboard_session_login')

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type='application/json'
        )

    def test_valid_staff_login_establishes_a_session(self):
        response = self._post({
            'email': 'staff@example.com', 'password': 'correct-horse-battery',
        })
        self.assertEqual(response.status_code, 200)
        # The session cookie is what protects the pages, and it must be HttpOnly
        # so page script cannot read it.
        self.assertIn('sessionid', response.cookies)
        self.assertTrue(response.cookies['sessionid']['httponly'])

        self.assertEqual(
            self.client.get(reverse('admin_dashboard_overview')).status_code, 200
        )

    def test_wrong_password_is_refused(self):
        response = self._post({'email': 'staff@example.com', 'password': 'nope'})
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('sessionid', response.cookies)

    def test_non_staff_cannot_sign_in_to_the_dashboard(self):
        User.objects.create_user(
            email='civilian@example.com', password='correct-horse-battery',
            first_name='Civ', last_name='Ilian',
        )
        response = self._post({
            'email': 'civilian@example.com', 'password': 'correct-horse-battery',
        })
        self.assertEqual(response.status_code, 401)

    def test_unknown_and_known_accounts_are_indistinguishable(self):
        unknown = self._post({'email': 'nobody@example.com', 'password': 'x'})
        known = self._post({'email': 'staff@example.com', 'password': 'x'})
        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(
            json.loads(unknown.content)['detail'],
            json.loads(known.content)['detail'],
        )

    def test_malformed_body_does_not_500(self):
        response = self.client.post(
            self.url, data='not json', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class StripeWebhookTests(TestCase):
    """
    The webhook used to parse the body unverified whenever STRIPE_WEBHOOK_SECRET
    was unset, so anyone could POST a forged checkout.session.completed and
    grant themselves a pro subscription.
    """

    def setUp(self):
        self.url = reverse('payments-stripe-webhook')
        self.user = User.objects.create_user(
            email='buyer@example.com', password='correct-horse-battery',
            first_name='Buy', last_name='Er',
        )

    def _forged_event(self):
        return json.dumps({
            'id': 'evt_forged',
            'type': 'checkout.session.completed',
            'data': {'object': {'client_reference_id': self.user.id}},
        })

    @mock.patch('django.conf.settings.STRIPE_WEBHOOK_SECRET', '')
    def test_unsigned_payload_is_refused_when_no_secret_configured(self):
        response = self.client.post(
            self.url, data=self._forged_event(), content_type='application/json'
        )
        self.assertEqual(response.status_code, 503)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_pro)

    @mock.patch('django.conf.settings.STRIPE_WEBHOOK_SECRET', 'whsec_test')
    def test_payload_without_signature_header_is_refused(self):
        response = self.client.post(
            self.url, data=self._forged_event(), content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_pro)

    @mock.patch('django.conf.settings.STRIPE_WEBHOOK_SECRET', 'whsec_test')
    def test_bad_signature_is_refused(self):
        response = self.client.post(
            self.url, data=self._forged_event(), content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=1,v1=deadbeef',
        )
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_pro)


class AudioLibraryTests(TestCase):
    """
    Covers the client's very first report: "I tried to upload an audio track and
    it uploaded to the wrong place. When I tried to delete it, it wouldn't
    delete either."
    """

    def setUp(self):
        from apps.parshas.models import Parsha

        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.is_superuser = True
        self.staff.save()
        self.client.force_login(self.staff)

        self.parsha = Parsha.objects.create(
            name='Bereshis', name_hebrew='בראשית', sefer='Bereshis',
            chapter_verse='1:1-6:8', haftorah_info='Yeshayahu 42:5-43:10',
        )
        self.url = '/api/v1/core/admin/audio_recordings/'

    def _audio(self, name='laining.mp3'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, b'ID3fake-audio-bytes', content_type='audio/mpeg')

    def test_upload_naming_a_parsha_becomes_a_track_the_app_can_see(self):
        from apps.content.models import AudioTrack

        response = self.client.post(self.url, {
            'title_english': 'Bereshis - Rishon',
            'category': 'Chumash (Parshios)',
            'parsha': self.parsha.id,
            'segment_type': 'Aliya 1',
            'audio_file': self._audio(),
        })

        self.assertEqual(response.status_code, 201, response.content)

        track = AudioTrack.objects.get()
        self.assertEqual(track.parsha, self.parsha)
        self.assertEqual(track.category, 'chumash')
        self.assertEqual(track.segment_type, 'Aliya 1')
        # Draft would be invisible in the app, which reads as a failed upload.
        self.assertEqual(track.status, 'published')

    def test_upload_without_a_parsha_still_works(self):
        from apps.audio_manager.models import AudioRecording

        response = self.client.post(self.url, {
            'title_english': 'Nusach for Yomim Noraim',
            'category': 'Nusach HaTefilla',
            'audio_file': self._audio(),
        })

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(AudioRecording.objects.count(), 1)

    def test_a_track_can_be_deleted(self):
        from apps.content.models import AudioTrack

        track = AudioTrack.objects.create(
            title='Bereshis - Rishon', audio_file=self._audio(),
            category='chumash', parsha=self.parsha, status='published',
        )

        # The listing hands back this exact id, so delete must accept it.
        listing = self.client.get(self.url).json()
        rows = listing['data'] if isinstance(listing, dict) else listing
        self.assertIn(f'track-{track.id}', [row['id'] for row in rows])

        response = self.client.delete(f'{self.url}track-{track.id}/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(AudioTrack.objects.filter(id=track.id).exists())

    def test_a_recording_can_still_be_deleted(self):
        from apps.audio_manager.models import AudioRecording

        rec = AudioRecording.objects.create(
            title_english='Standalone', category='Megillos',
            audio_file=self._audio(),
        )
        response = self.client.delete(f'{self.url}{rec.id}/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(AudioRecording.objects.filter(id=rec.id).exists())


class LoginLockoutTests(TestCase):
    """
    The audit reported no rate limiting or lockout on sign-in.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.save()
        self.url = reverse('admin_dashboard_session_login')

    def _attempt(self, password):
        return self.client.post(
            self.url,
            data=json.dumps({'email': 'staff@example.com', 'password': password}),
            content_type='application/json',
        )

    def test_repeated_failures_lock_the_account(self):
        from apps.core.ratelimit import MAX_FAILURES_PER_ACCOUNT

        for _ in range(MAX_FAILURES_PER_ACCOUNT - 1):
            self.assertEqual(self._attempt('wrong').status_code, 401)

        # The one that trips the limit, and everything after it.
        self.assertEqual(self._attempt('wrong').status_code, 429)
        self.assertEqual(self._attempt('wrong').status_code, 429)

    def test_lockout_holds_even_against_the_right_password(self):
        from apps.core.ratelimit import MAX_FAILURES_PER_ACCOUNT

        for _ in range(MAX_FAILURES_PER_ACCOUNT):
            self._attempt('wrong')

        # Otherwise an attacker who guesses correctly on attempt 50 still wins.
        response = self._attempt('correct-horse-battery')
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('sessionid', response.cookies)

    def test_a_successful_sign_in_clears_the_counter(self):
        self._attempt('wrong')
        self._attempt('wrong')

        self.assertEqual(self._attempt('correct-horse-battery').status_code, 200)

        self.client.logout()
        # Budget is full again, so a later typo is not penalised by old failures.
        self.assertEqual(self._attempt('wrong').status_code, 401)


class TwoFactorTests(TestCase):
    """
    The login page advertised "2FA Enabled" while nothing was implemented.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.save()
        self.login_url = reverse('admin_dashboard_session_login')
        self.setup_url = reverse('admin_dashboard_2fa_setup')

    def _sign_in(self, otp=None):
        body = {'email': 'staff@example.com', 'password': 'correct-horse-battery'}
        if otp is not None:
            body['otp'] = otp
        return self.client.post(
            self.login_url, data=json.dumps(body), content_type='application/json'
        )

    def _enrol(self):
        """Completes enrolment, returning (secret, recovery_codes)."""
        import pyotp

        self.client.force_login(self.staff)
        secret = self.client.get(self.setup_url).json()['secret']
        response = self.client.post(
            self.setup_url,
            data=json.dumps({'otp': pyotp.TOTP(secret).now()}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        codes = response.json()['recovery_codes']
        self.client.logout()
        self.staff.refresh_from_db()
        return secret, codes

    def test_enrolment_requires_a_matching_code(self):
        self.client.force_login(self.staff)
        self.client.get(self.setup_url)

        response = self.client.post(
            self.setup_url, data=json.dumps({'otp': '000000'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

        self.staff.refresh_from_db()
        # Not enabled, so an abandoned enrolment cannot lock the admin out.
        self.assertIsNone(self.staff.totp_confirmed_at)

    def test_enrolment_enables_it_and_issues_recovery_codes(self):
        _, codes = self._enrol()
        self.assertIsNotNone(self.staff.totp_confirmed_at)
        self.assertEqual(len(codes), 8)
        # Stored hashed, never in the clear.
        for code in codes:
            self.assertNotIn(code, self.staff.totp_recovery_codes)

    def test_password_alone_is_no_longer_enough(self):
        self._enrol()
        response = self._sign_in()
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response.json()['otp_required'])
        self.assertNotIn('sessionid', response.cookies)

    def test_correct_code_signs_in(self):
        import pyotp

        secret, _ = self._enrol()
        response = self._sign_in(pyotp.TOTP(secret).now())
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            self.client.get(reverse('admin_dashboard_overview')).status_code, 200
        )

    def test_wrong_code_is_refused(self):
        self._enrol()
        self.assertEqual(self._sign_in('000000').status_code, 401)

    def test_a_recovery_code_works_once(self):
        _, codes = self._enrol()

        self.assertEqual(self._sign_in(codes[0]).status_code, 200)
        self.client.logout()

        # Single use — replaying it must fail.
        self.assertEqual(self._sign_in(codes[0]).status_code, 401)
        # The others still work.
        self.assertEqual(self._sign_in(codes[1]).status_code, 200)

    def test_accounts_without_2fa_are_unaffected(self):
        self.assertEqual(self._sign_in().status_code, 200)

    def test_disabling_requires_the_password(self):
        self._enrol()
        self.client.force_login(self.staff)
        url = reverse('admin_dashboard_2fa_disable')

        self.assertEqual(
            self.client.post(
                url, data=json.dumps({'password': 'wrong'}),
                content_type='application/json',
            ).status_code,
            403,
        )
        self.staff.refresh_from_db()
        self.assertIsNotNone(self.staff.totp_confirmed_at)

        self.assertEqual(
            self.client.post(
                url, data=json.dumps({'password': 'correct-horse-battery'}),
                content_type='application/json',
            ).status_code,
            200,
        )
        self.staff.refresh_from_db()
        self.assertIsNone(self.staff.totp_confirmed_at)

    def test_setup_is_staff_only(self):
        User.objects.create_user(
            email='civilian@example.com', password='correct-horse-battery',
            first_name='Civ', last_name='Ilian',
        )
        self.client.login(email='civilian@example.com', password='correct-horse-battery')
        self.assertEqual(self.client.get(self.setup_url).status_code, 403)


class NotificationRecipientCountTests(TestCase):
    """
    The dashboard reported 50 and 100 recipients on an install with five users.
    recipients_count is a stored snapshot, so rows written by hand or at another
    time kept a stale figure forever.
    """

    def setUp(self):
        from apps.users_and_subs.models import UserProfile

        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.is_superuser = True
        self.staff.save()

        # Five users total: two paying, three not (staff included).
        paid = User.objects.create_user(
            email='paid@example.com', password='x', first_name='P', last_name='One',
        )
        paid.is_pro = True
        paid.save()

        profile_paid = User.objects.create_user(
            email='profile@example.com', password='x', first_name='P', last_name='Two',
        )
        UserProfile.objects.update_or_create(
            user=profile_paid, defaults={'subscription_type': 'Yearly $49'},
        )

        User.objects.create_user(
            email='free1@example.com', password='x', first_name='F', last_name='One',
        )
        User.objects.create_user(
            email='free2@example.com', password='x', first_name='F', last_name='Two',
        )

        self.client.force_login(self.staff)
        self.url = '/api/v1/core/admin/notifications/'

    def _create(self, audience):
        response = self.client.post(self.url, {
            'title': 'Test', 'message': 'Body', 'audience': audience,
        })
        self.assertEqual(response.status_code, 201, response.content)
        from apps.core.models import AdminNotification
        return AdminNotification.objects.latest('created_at')

    def test_counts_reflect_the_real_user_base(self):
        self.assertEqual(self._create('all').recipients_count, User.objects.count())

    def test_pro_audience_includes_paid_profiles_not_just_the_flag(self):
        # Counting only is_pro would say 1 and disagree with the analytics page.
        self.assertEqual(self._create('pro').recipients_count, 2)

    def test_free_is_everyone_else(self):
        self.assertEqual(self._create('free').recipients_count, 3)
        self.assertEqual(
            self._create('free').recipients_count + self._create('pro').recipients_count,
            User.objects.count(),
        )

    def test_a_stale_count_is_repaired_by_the_command(self):
        from django.core.management import call_command
        from apps.core.models import AdminNotification

        notification = self._create('all')
        AdminNotification.objects.filter(id=notification.id).update(recipients_count=100)

        call_command('recount_notifications', verbosity=0)

        notification.refresh_from_db()
        self.assertEqual(notification.recipients_count, User.objects.count())


class SiteSettingsTests(TestCase):
    """
    The settings page showed empty fields, "undefined" values, and a timezone
    of Asia/Dhaka that reverted on every load.
    """

    def setUp(self):
        self.staff = User.objects.create_user(
            email='staff@example.com', password='correct-horse-battery',
            first_name='Staff', last_name='Member',
        )
        self.staff.is_staff = True
        self.staff.is_superuser = True
        self.staff.save()
        self.client.force_login(self.staff)
        self.url = '/api/v1/core/admin/settings/'

    def test_settings_response_carries_the_expected_fields(self):
        body = self.client.get(self.url).json()
        # The page reads these off `data`; the bug was reading them off the
        # wrapper, where every one of them is undefined.
        payload = body['data'] if isinstance(body, dict) and 'data' in body else body

        for field in [
            'email_reports', 'auto_publish_uploads', 'payment_alerts',
            'default_upload_status', 'library_page_size', 'timezone',
            'admin_profile',
        ]:
            self.assertIn(field, payload)

        self.assertEqual(payload['admin_profile']['email'], 'staff@example.com')

    def test_timezone_does_not_default_to_the_dev_teams_zone(self):
        from apps.core.models import SiteSettings
        self.assertEqual(SiteSettings.get_settings().timezone, 'America/New_York')

    def test_timezone_persists_across_a_save(self):
        from apps.core.models import SiteSettings

        response = self.client.post(self.url, data=json.dumps({
            'timezone': 'Asia/Jerusalem', 'library_page_size': 30,
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)

        # Previously there was no field to save into, so it reset every load.
        SiteSettings.objects.all().update()  # bypass the cached singleton
        from django.core.cache import cache
        cache.delete('site_settings')
        self.assertEqual(SiteSettings.get_settings().timezone, 'Asia/Jerusalem')


class PublicPageTests(TestCase):
    """
    The audit found no privacy, terms, support, robots.txt or sitemap pages, and
    a homepage serving raw API JSON.
    """

    def test_homepage_is_a_landing_page_not_api_json(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])
        self.assertNotIn(b'"status": "operational"', response.content)

    def test_public_pages_are_reachable_anonymously(self):
        for path in ['/support/', '/privacy/', '/terms/']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_legal_stubs_say_plainly_that_they_are_unpublished(self):
        # Better an honest placeholder than invented policy text that
        # misdescribes what actually happens to a subscriber's data.
        for path in ['/privacy/', '/terms/']:
            with self.subTest(path=path):
                self.assertIn(b'Not yet published', self.client.get(path).content)

    def test_robots_disallows_the_api_and_dashboard(self):
        body = self.client.get('/robots.txt').content
        self.assertIn(b'Disallow: /api/', body)
        self.assertIn(b'Disallow: /dashboard/', body)

    def test_sitemap_is_valid_xml_listing_the_public_pages(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        for path in [b'/support/', b'/privacy/', b'/terms/']:
            self.assertIn(path, response.content)

    def test_api_root_still_answers_for_monitoring(self):
        self.assertEqual(self.client.get('/api/').status_code, 200)


class DemoContentAuditTests(TestCase):
    """
    The client saw test data in notifications and testimonials. Those rows live
    in the production database, so the deliverable is a safe way to find them.
    """

    def setUp(self):
        from apps.content.models import Testimonial

        self.real_user = User.objects.create_user(
            email='real@ezlain.app', password='x', first_name='R', last_name='Eal',
        )
        self.test_user = User.objects.create_user(
            email='qa@example.com', password='x', first_name='Q', last_name='A',
        )

        self.genuine = Testimonial.objects.create(
            user=self.real_user, author_name='A Parent',
            content='My son learned his whole parsha with this.', is_approved=True,
        )
        self.placeholder = Testimonial.objects.create(
            user=self.real_user, author_name='Tester',
            content='Lorem ipsum dolor sit amet', is_approved=True,
        )
        self.from_test_account = Testimonial.objects.create(
            user=self.test_user, author_name='QA', content='checking', is_approved=True,
        )

    def _run(self, *args):
        from io import StringIO
        from django.core.management import call_command

        out = StringIO()
        call_command('find_demo_content', *args, stdout=out)
        return out.getvalue()

    def test_reports_without_deleting_by_default(self):
        from apps.content.models import Testimonial

        output = self._run()
        self.assertIn('Lorem ipsum', output)
        self.assertIn('qa@example.com', output)
        # Nothing removed until asked.
        self.assertEqual(Testimonial.objects.count(), 3)

    def test_leaves_genuine_testimonials_alone(self):
        from apps.content.models import Testimonial

        self._run('--delete')
        remaining = list(Testimonial.objects.values_list('id', flat=True))
        self.assertIn(self.genuine.id, remaining)
        self.assertNotIn(self.placeholder.id, remaining)
        self.assertNotIn(self.from_test_account.id, remaining)

    def test_finds_accounts_on_reserved_domains(self):
        self.assertIn('qa@example.com', self._run())
