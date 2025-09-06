#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benchstay.settings')
django.setup()

from hotelkit.views import RepairsDashboardView
from django.test import RequestFactory
from django.contrib.auth.models import User

def debug_dashboard():
    try:
        rf = RequestFactory()
        request = rf.get('/hotelkit/repairs/dashboard/')
        user = User.objects.first()
        request.user = user
        
        view = RepairsDashboardView()
        view.request = request
        
        print("Testing context creation...")
        context = view.get_context_data()
        print("Context created successfully!")
        print("Context keys:", list(context.keys()))
        
        # Test each JSON serialization
        print("\nTesting JSON serialization...")
        for key in ['trends', 'types', 'heatmap', 'sla_data']:
            if key in context:
                try:
                    import json
                    from hotelkit.views import json_serializer
                    json.dumps(context[key], default=json_serializer)
                    print(f"✓ {key} serializes successfully")
                except Exception as e:
                    print(f"✗ {key} serialization failed: {e}")
                    print(f"  Data type: {type(context[key])}")
                    if hasattr(context[key], '__len__') and len(context[key]) > 0:
                        print(f"  First item: {context[key][0]}")
                        print(f"  First item type: {type(context[key][0])}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_dashboard()
