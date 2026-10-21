from django import forms
from django.contrib.auth.models import User
from accounts.models import Profile
from .models import Product, Category, Person


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'barcode', 'name', 'category', 'description',
            'inventary_min', 'price_in', 'price_out',
            'unit', 'presentation', 'image', 'is_active'
        ]
        widgets = {
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 750100000001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción opcional'}),
            'inventary_min': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'price_in': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'price_out': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Pieza, Kg, Litro'}),
            'presentation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Caja, Botella, Bolsa'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            'name', 'lastname', 'company',
            'phone1', 'phone2', 'email1', 'email2',
            'address1', 'address2', 'image', 'kind'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre o razón social'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Empresa'}),
            'phone1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono principal'}),
            'phone2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono secundario'}),
            'email1': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'email2': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo2@ejemplo.com'}),
            'address1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección principal'}),
            'address2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dirección secundaria'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'kind': forms.Select(attrs={'class': 'form-select'}),
        }


class UserCreateForm(forms.ModelForm):
    kind = forms.ChoiceField(
        choices=Profile.KIND_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Rol del usuario"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        label="Contraseña"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s)'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.kind = int(self.cleaned_data['kind'])
            profile.save()
        return user


class UserUpdateForm(forms.ModelForm):
    kind = forms.ChoiceField(
        choices=Profile.KIND_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Rol del usuario"
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Dejar en blanco para no cambiar'}),
        label="Nueva contraseña (opcional)"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['kind'].initial = self.instance.profile.kind

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get('password')
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.kind = int(self.cleaned_data['kind'])
            profile.save()
        return user
