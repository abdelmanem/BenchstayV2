from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.conf import settings
from .models import UserProfile
import django

# Debug view to check settings and templates
def debug_info(request):
    """Debug view to check settings and templates"""
    from django.template.loader import get_template
    
    # Try to load the admin_settings template
    try:
        template = get_template('accounts/admin_settings.html')
        template_exists = True
    except Exception as e:
        template_exists = False
        template_error = str(e)
    
    # Check if dashboard_base.html exists
    try:
        base_template = get_template('dashboard_base.html')
        base_template_exists = True
    except Exception as e:
        base_template_exists = False
        base_template_error = str(e)
    
    debug_info = {
        'DEBUG': settings.DEBUG,
        'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
        'TEMPLATE_DIRS': [t.get('DIRS', []) for t in settings.TEMPLATES],
        'STATIC_URL': settings.STATIC_URL,
        'MEDIA_URL': settings.MEDIA_URL,
        'admin_settings_template_exists': template_exists,
        'dashboard_base_template_exists': base_template_exists,
    }
    
    if not template_exists:
        debug_info['template_error'] = template_error
    
    if not base_template_exists:
        debug_info['base_template_error'] = base_template_error
        
    return HttpResponse(f"<pre>{debug_info}</pre>")

def help_page(request):
    """Help page with app information and version details"""
    # Get Django version
    django_version = django.get_version()
    
    # Get app information
    app_info = {
        'name': 'Benchstay',
        'version': '2.0.0',  # You can update this with your actual version
        'description': 'Hotel Benchmarking Platform',
        'developer': 'Your Company Name',
        'contact': 'support@example.com',
        'django_version': django_version,
        'python_version': settings.PYTHON_VERSION if hasattr(settings, 'PYTHON_VERSION') else 'Not specified',
    }
    
    # Get database info (safely)
    db_info = {
        'engine': settings.DATABASES['default']['ENGINE'].split('.')[-1],
        'name': settings.DATABASES['default']['NAME'],
    }
    
    context = {
        'app_info': app_info,
        'db_info': db_info,
    }
    
    return render(request, 'accounts/help.html', context)

def home(request):
    """Home page view that redirects to login if not authenticated"""
    if request.user.is_authenticated:
        return redirect('hotel_management:home')
    return redirect('accounts:login')

def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('hotel_management:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('hotel_management:home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'accounts/login.html', {'title': 'Login - Benchstay'})

@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('accounts:login')

@login_required
def profile(request):
    """User profile view and edit"""
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user information
        request.user.first_name = request.POST.get('first_name')
        request.user.last_name = request.POST.get('last_name')
        request.user.email = request.POST.get('email')
        request.user.save()
        
        # Update profile information
        user_profile.position = request.POST.get('position')
        user_profile.phone_number = request.POST.get('phone_number')
        user_profile.save()
        
        messages.success(request, 'Profile updated successfully')
        return redirect('accounts:profile')
    
    context = {
        'title': 'User Profile - Benchstay',
        'user_profile': user_profile
    }
    return render(request, 'accounts/profile.html', context)



@login_required
def admin_settings(request):
    """Admin settings view - only accessible to admin users"""
    # Check if user is admin
    try:
        # Get or create the user profile
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if not profile.is_admin:
            messages.error(request, 'You do not have permission to access this page')
            return redirect('hotel_management:home')
    except Exception as e:
        # Log the error for debugging
        print(f"Error in admin_settings view: {str(e)}")
        messages.error(request, 'An error occurred. Please contact the administrator.')
        return redirect('hotel_management:home')
    
    users = User.objects.all()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Handle user actions that require user_id
        if action in ['make_admin', 'remove_admin', 'delete_user', 'reset_password', 'activate_user', 'deactivate_user']:
            user_id = request.POST.get('user_id')
            if not user_id:
                messages.error(request, 'User ID is required')
                return redirect('accounts:admin_settings')
                
            try:
                user = User.objects.get(id=user_id)
                profile, created = UserProfile.objects.get_or_create(user=user)
                
                if action == 'make_admin':
                    profile.is_admin = True
                    profile.save()
                    messages.success(request, f'{user.username} is now an admin')
                
                elif action == 'remove_admin':
                    profile.is_admin = False
                    profile.save()
                    messages.success(request, f'{user.username} is no longer an admin')
                
                elif action == 'delete_user':
                    user.delete()
                    messages.success(request, f'User {user.username} has been deleted')
                
                elif action == 'reset_password':
                    new_password = request.POST.get('new_password')
                    confirm_password = request.POST.get('confirm_password')
                    
                    if new_password != confirm_password:
                        messages.error(request, 'Passwords do not match')
                    else:
                        user.set_password(new_password)
                        user.save()
                        messages.success(request, f'Password for {user.username} has been reset')
                
                elif action == 'activate_user':
                    user.is_active = True
                    user.save()
                    messages.success(request, f'{user.username} has been activated')
                
                elif action == 'deactivate_user':
                    user.is_active = False
                    user.save()
                    messages.success(request, f'{user.username} has been deactivated')
                    
            except User.DoesNotExist:
                messages.error(request, 'User not found')
        
        # Handle adding a new user
        elif action == 'add_user':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            position = request.POST.get('position', '')
            phone_number = request.POST.get('phone_number', '')
            is_admin = request.POST.get('is_admin') == 'on'
            
            # Validate required fields
            if not (username and email and password):
                messages.error(request, 'Username, email, and password are required')
                return redirect('accounts:admin_settings')
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return redirect('accounts:admin_settings')
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return redirect('accounts:admin_settings')
            
            # Create user
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Create user profile
                profile = UserProfile.objects.create(
                    user=user,
                    position=position,
                    phone_number=phone_number,
                    is_admin=is_admin
                )
                
                messages.success(request, f'User {username} has been created successfully')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
    
    context = {
        'title': 'Admin Settings - Benchstay',
        'users': users
    }
    return render(request, 'accounts/admin_settings.html', context)
