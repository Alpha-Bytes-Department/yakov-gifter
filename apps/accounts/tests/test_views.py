from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

from django.test import override_settings

User = get_user_model()

@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True, CELERY_RESULT_BACKEND='cache+memory://')
class AuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.profile_url = reverse('users-me')
        self.user_data = {
            "full_name": "Test User",
            "email": "testuser@example.com",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!"
        }

    def test_registration_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['email'], self.user_data['email'])

    def test_login_success(self):
        # First register
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Then login
        login_data = {
            "email": self.user_data['email'],
            "password": self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data['tokens'])

    def test_get_profile_success(self):
        # Register and Login to get token
        self.client.post(self.register_url, self.user_data, format='json')
        login_data = {
            "email": self.user_data['email'],
            "password": self.user_data['password']
        }
        login_response = self.client.post(self.login_url, login_data, format='json')
        token = login_response.data['tokens']['access']

        # Access profile
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user_data['email'])
