from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import (
    UserRegisterForm,
    UserLoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
    StyledPasswordChangeForm
)
from .models import Profile

def home_view(request):
    return render(request, 'home.html', {
        'total_users': User.objects.count()
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Cuenta creada. Ya puedes iniciar sesión.")
            return redirect('login')
        else:
            messages.error(request, "Revisa los campos del formulario.")
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        if '@' in username_or_email:
            try:
                matched_user = User.objects.get(email__iexact=username_or_email)
                username_to_check = matched_user.username
            except User.DoesNotExist:
                username_to_check = username_or_email
        else:
            username_to_check = username_or_email

        user = authenticate(request, username=username_to_check, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(1209600)

                messages.success(request, f"Bienvenido, {user.first_name or user.username}.")
                next_url = request.GET.get('next')
                return redirect(next_url if next_url else 'dashboard')
            else:
                messages.error(request, "Esta cuenta está desactivada.")
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "Has cerrado sesión.")
    return redirect('login')

@login_required
def dashboard_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    fields_to_check = [
        request.user.first_name,
        request.user.last_name,
        request.user.email,
        profile.phone,
        profile.address,
        profile.bio,
        profile.avatar
    ]
    completed = sum(1 for f in fields_to_check if f)
    completion_percentage = int((completed / len(fields_to_check)) * 100)

    context = {
        'profile': profile,
        'completion_percentage': completion_percentage,
        'recent_users': User.objects.order_by('-date_joined')[:5] if request.user.is_staff else [],
    }
    return render(request, 'accounts/dashboard.html', context)

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect('profile')
        else:
            messages.error(request, "Revisa los datos.")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Contraseña actualizada.")
            return redirect('profile')
        else:
            messages.error(request, "Revisa los datos.")
    else:
        form = StyledPasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})
