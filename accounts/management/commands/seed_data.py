from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile

class Command(BaseCommand):
    help = 'Crea usuarios iniciales para el proyecto RegilogPy'

    def handle(self, *args, **options):
        admin_username = 'admin'
        admin_email = 'admin@regilogpy.local'
        admin_pass = 'admin'

        if not User.objects.filter(username=admin_username).exists():
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_pass,
                first_name='Administrador',
                last_name='Sistema'
            )
            admin_user.profile.phone = '+52 55 1234 5678'
            admin_user.profile.address = 'Oficina Central'
            admin_user.profile.bio = 'Administrador del sistema.'
            admin_user.profile.save()
            self.stdout.write(self.style.SUCCESS(f"Superusuario '{admin_username}' creado con contraseña '{admin_pass}'."))
        else:
            self.stdout.write(self.style.WARNING(f"El usuario '{admin_username}' ya existe."))

        demo_username = 'usuario_demo'
        demo_email = 'demo@regilogpy.local'
        demo_pass = 'demo1234'

        if not User.objects.filter(username=demo_username).exists():
            demo_user = User.objects.create_user(
                username=demo_username,
                email=demo_email,
                password=demo_pass,
                first_name='Carlos',
                last_name='Mendoza'
            )
            demo_user.profile.phone = '+52 55 9876 5432'
            demo_user.profile.address = 'Av. Reforma 222, CDMX'
            demo_user.profile.bio = 'Usuario del sistema.'
            demo_user.profile.save()
            self.stdout.write(self.style.SUCCESS(f"Usuario demo '{demo_username}' creado con contraseña '{demo_pass}'."))
        else:
            self.stdout.write(self.style.WARNING(f"El usuario '{demo_username}' ya existe."))
