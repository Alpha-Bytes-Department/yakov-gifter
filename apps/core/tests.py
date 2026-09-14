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
