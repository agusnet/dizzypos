from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import Profile

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_password = 'Password123!'
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password=self.user_password,
            first_name='Test',
            last_name='User'
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'RegilogPy')

    def test_user_registration_success(self):
        register_data = {
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'username': 'marialopez',
            'email': 'maria@example.com',
            'phone': '1234567890',
            'password': 'StrongPassword99!',
            'password_confirm': 'StrongPassword99!',
            'terms': True
        }
        response = self.client.post(reverse('register'), data=register_data)
        # Debería redirigir al login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

        # Verificar que el usuario y su perfil existen
        user_created = User.objects.get(username='marialopez')
        self.assertEqual(user_created.email, 'maria@example.com')
        self.assertTrue(user_created.check_password('StrongPassword99!'))
        self.assertTrue(hasattr(user_created, 'profile'))
        self.assertEqual(user_created.profile.phone, '1234567890')

    def test_user_registration_mismatched_passwords(self):
        register_data = {
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'username': 'marialopez',
            'email': 'maria@example.com',
            'password': 'PasswordOne1!',
            'password_confirm': 'PasswordTwo2!',
            'terms': True
        }
        response = self.client.post(reverse('register'), data=register_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='marialopez').exists())

    def test_user_login_with_username(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': self.user_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_user_login_with_email(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser@example.com',
            'password': self.user_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_user_login_invalid_password(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'WrongPassword!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrectos')

    def test_logout(self):
        self.client.login(username='testuser', password=self.user_password)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_dashboard_authenticated(self):
        self.client.login(username='testuser', password=self.user_password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_profile_update(self):
        self.client.login(username='testuser', password=self.user_password)
        update_data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'email': 'updated@example.com',
            'phone': '555-4321',
            'address': 'Nueva Dirección 123',
            'bio': 'Esta es una nueva biografía.'
        }
        response = self.client.post(reverse('profile'), data=update_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.profile.phone, '555-4321')
        self.assertEqual(self.user.profile.address, 'Nueva Dirección 123')
