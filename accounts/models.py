from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    KIND_ADMIN = 1
    KIND_SELLER = 2
    KIND_CHOICES = (
        (KIND_ADMIN, 'Administrador'),
        (KIND_SELLER, 'Vendedor'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Usuario")
    kind = models.IntegerField(choices=KIND_CHOICES, default=KIND_SELLER, verbose_name="Tipo de usuario")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Teléfono")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Dirección")
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name="Foto de perfil")
    bio = models.TextField(blank=True, null=True, verbose_name="Biografía")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última modificación")

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuarios"

    def __str__(self):
        return f"{self.user.username} ({self.get_kind_display()})"

    @property
    def is_admin(self):
        return self.kind == self.KIND_ADMIN or self.user.is_superuser

    @property
    def is_seller(self):
        return not self.is_admin

    @property
    def full_name(self):
        full = f"{self.user.first_name} {self.user.last_name}".strip()
        return full if full else self.user.username

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        name_for_avatar = self.user.first_name or self.user.username
        return f"https://ui-avatars.com/api/?name={name_for_avatar}&background=4f46e5&color=fff&size=128&bold=true"
