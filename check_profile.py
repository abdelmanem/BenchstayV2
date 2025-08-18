# Script to check if user 'mon' has a UserProfile with is_admin set to True
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benchstay.settings')
django.setup()

from accounts.models import UserProfile
from django.contrib.auth.models import User

try:
    user = User.objects.get(username='mon')
    print(f"User found: {user.username}")
    
    try:
        profile = UserProfile.objects.get(user=user)
        print(f"Profile found: {profile.id}")
        print(f"Is admin: {profile.is_admin}")
    except UserProfile.DoesNotExist:
        print("UserProfile does not exist for this user")
        
        # Create profile with is_admin=True
        profile = UserProfile.objects.create(user=user, is_admin=True)
        print(f"Created profile with is_admin=True")
        
except User.DoesNotExist:
    print("User 'mon' not found")