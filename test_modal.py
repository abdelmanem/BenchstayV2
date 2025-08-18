import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benchstay.settings_production')
django.setup()

# Import necessary modules
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User
from accounts.models import UserProfile

# Create a test client
client = Client()

# Create a test user with admin privileges if it doesn't exist
username = 'testadmin'
password = 'testpassword123'
try:
    user = User.objects.get(username=username)
except User.DoesNotExist:
    user = User.objects.create_user(username=username, password=password)
    UserProfile.objects.create(user=user, is_admin=True)
else:
    # Make sure the user has admin privileges
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.is_admin = True
    profile.save()

# Log in
logged_in = client.login(username=username, password=password)
print(f"Login successful: {logged_in}")

# Check if the admin settings page is accessible
response = client.get('/accounts/admin-settings/', HTTP_HOST='127.0.0.1:8000')
print(f"Admin settings page status code: {response.status_code}")

# Check if the page contains the modal HTML
if 'modal fade' in response.content.decode():
    print("Modal HTML found in the page")
    # Check if Bootstrap JS is included
    if 'bootstrap.bundle.min.js' in response.content.decode():
        print("Bootstrap JS is included in the page")
    else:
        print("WARNING: Bootstrap JS is NOT included in the page")
    
    # Check if jQuery is included (sometimes needed for Bootstrap modals)
    if 'jquery' in response.content.decode().lower():
        print("jQuery is included in the page")
    else:
        print("NOTE: jQuery is NOT included in the page (may not be needed with Bootstrap 5)")
    
    # Check for modal trigger elements
    if 'data-bs-toggle="modal"' in response.content.decode():
        print("Modal trigger elements found")
    else:
        print("WARNING: No modal trigger elements found")
    
    # Check for modal close elements
    if 'data-bs-dismiss="modal"' in response.content.decode():
        print("Modal close elements found")
    else:
        print("WARNING: No modal close elements found")
else:
    print("WARNING: No modal HTML found in the page")

# Check if there are any custom JavaScript files that might interfere
if 'script src="' in response.content.decode():
    scripts = [line for line in response.content.decode().split('\n') if 'script src="' in line]
    print("\nCustom JavaScript files:")
    for script in scripts:
        print(f"  - {script.strip()}")

# Check if DEBUG mode is enabled
from django.conf import settings
print(f"\nDEBUG mode: {settings.DEBUG}")

# Check if the CSRF token is present in the form
if 'csrfmiddlewaretoken' in response.content.decode():
    print("CSRF token is present in the form")
else:
    print("WARNING: CSRF token is NOT present in the form")

print("\nTest completed.")