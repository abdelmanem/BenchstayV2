import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benchstay.settings_production')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

# Create a test user if it doesn't exist
username = 'TestUser'
password = 'testpassword123'

try:
    user = User.objects.get(username__iexact=username)
    print(f"User '{username}' already exists with actual username: {user.username}")
except User.DoesNotExist:
    user = User.objects.create_user(username=username, password=password)
    print(f"Created user '{username}'")

# Test authentication with different case variations
test_cases = [
    username,  # Original case
    username.lower(),  # All lowercase
    username.upper(),  # All uppercase
    username.capitalize(),  # First letter capitalized
]

print("\nTesting case-insensitive login:")
for test_username in test_cases:
    user = authenticate(username=test_username, password=password)
    if user:
        print(f"✓ Successfully authenticated with username '{test_username}'")
    else:
        print(f"✗ Failed to authenticate with username '{test_username}'")