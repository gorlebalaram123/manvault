from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import User, Address, OTPVerification
from .forms import RegisterForm, LoginForm, ProfileForm, AddressForm
from notifications.utils import notify, send_otp_email

def register_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        user.save()
        # Send email verification OTP
        otp = OTPVerification.objects.create(user=user, otp_type='email_verify')
        send_otp_email(user, otp.code, "email verification")
        request.session['verify_user_id'] = user.id
        messages.success(request, f'Welcome! Please verify your email to continue.')
        return redirect('accounts:verify_email')
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    form = LoginForm(request, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Welcome back, {user.first_name or user.username}! 👋')
        return redirect(request.GET.get('next', 'store:home'))
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('store:home')

def verify_email(request):
    user_id = request.session.get('verify_user_id')
    if not user_id:
        return redirect('accounts:login')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        otp = OTPVerification.objects.filter(user=user, otp_type='email_verify', is_used=False).last()
        if otp and otp.is_valid and otp.code == code:
            otp.is_used = True; otp.save()
            user.email_verified = True; user.save()
            login(request, user)
            del request.session['verify_user_id']
            notify(user, 'Welcome to ManVault! 🎉', 'Your account is verified. Happy shopping!', 'system')
            messages.success(request, 'Email verified! Welcome to ManVault 🎉')
            return redirect('store:home')
        else:
            messages.error(request, 'Invalid or expired OTP.')
    return render(request, 'accounts/verify_email.html', {'user': user})

def resend_otp(request):
    user_id = request.session.get('verify_user_id')
    if user_id:
        user = get_object_or_404(User, id=user_id)
        OTPVerification.objects.filter(user=user, otp_type='email_verify', is_used=False).update(is_used=True)
        otp = OTPVerification.objects.create(user=user, otp_type='email_verify')
        send_otp_email(user, otp.code, "email verification")
        messages.success(request, 'OTP resent to your email!')
    return redirect('accounts:verify_email')

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email','').strip()
        try:
            user = User.objects.get(email=email)
            otp = OTPVerification.objects.create(user=user, otp_type='password_reset')
            send_otp_email(user, otp.code, "password reset")
            request.session['reset_user_id'] = user.id
            messages.success(request, 'OTP sent to your email.')
            return redirect('accounts:reset_password')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email.')
    return render(request, 'accounts/forgot_password.html')

def reset_password(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('accounts:forgot_password')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        code = request.POST.get('otp','').strip()
        new_pass = request.POST.get('new_password','')
        otp = OTPVerification.objects.filter(user=user, otp_type='password_reset', is_used=False).last()
        if otp and otp.is_valid and otp.code == code:
            otp.is_used = True; otp.save()
            user.set_password(new_pass)
            user.save()
            del request.session['reset_user_id']
            messages.success(request, 'Password reset! Please log in.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Invalid or expired OTP.')
    return render(request, 'accounts/reset_password.html')

@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Profile updated!')
        return redirect('accounts:profile')
    addresses = request.user.addresses.all()
    from orders.models import Order
    orders = request.user.orders.all()[:5]
    from store.models import Wishlist
    try: wishlist_count = request.user.wishlist.products.count()
    except: wishlist_count = 0
    return render(request, 'accounts/profile.html', {
        'form': form, 'addresses': addresses, 'orders': orders,
        'wishlist_count': wishlist_count
    })

@login_required
def add_address(request):
    form = AddressForm(request.POST or None)
    if form.is_valid():
        addr = form.save(commit=False); addr.user = request.user; addr.save()
        messages.success(request, 'Address added!')
        return redirect(request.POST.get('next', 'accounts:profile'))
    return render(request, 'accounts/address_form.html', {'form': form, 'title': 'Add Address'})

@login_required
def edit_address(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=addr)
    if form.is_valid():
        form.save(); messages.success(request, 'Address updated!')
        return redirect('accounts:profile')
    return render(request, 'accounts/address_form.html', {'form': form, 'title': 'Edit Address'})

@login_required
def delete_address(request, pk):
    addr = get_object_or_404(Address, pk=pk, user=request.user)
    addr.delete(); messages.success(request, 'Address removed.')
    return redirect('accounts:profile')
