#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benchstay.settings')
django.setup()

from hotel_management.models import BudgetGoal, Hotel
from datetime import date

# Get the hotel
hotel = Hotel.objects.first()
print(f"Hotel: {hotel}")

# Test the date range for September 2025
start_date = date(2025, 9, 1)
end_date = date(2025, 9, 30)
days_diff = (end_date - start_date).days
fiscal_year = start_date.year

print(f"\nTesting date range: {start_date} to {end_date} ({days_diff} days)")
print(f"Fiscal year: {fiscal_year}")

# Get all budget goals for this hotel and fiscal year
existing_goals = BudgetGoal.objects.filter(hotel=hotel, fiscal_year=fiscal_year)
print(f"\nExisting goals for this hotel and fiscal year:")
for goal in existing_goals:
    print(f"  - {goal.period_type} '{goal.period_detail}' (id: {goal.id})")

# Test the goal finding logic
try:
    # Priority 1: Look for monthly goals that match the month
    if days_diff <= 31:  # Less than or equal to a month
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        # Check if start_date and end_date are in the same month
        if start_date.month == end_date.month and start_date.year == end_date.year:
            period_detail = month_names[start_date.month - 1]
            print(f"\nLooking for monthly goal with period_detail: '{period_detail}'")
            budget_goal = existing_goals.filter(
                period_type='monthly',
                period_detail=period_detail
            ).first()
            
            if budget_goal:
                print(f"✅ Found matching monthly goal: {budget_goal}")
                print(f"   - ID: {budget_goal.id}")
                print(f"   - Period Type: {budget_goal.period_type}")
                print(f"   - Period Detail: '{budget_goal.period_detail}'")
                print(f"   - Occupancy Goal: {budget_goal.occupancy_goal}")
            else:
                print(f"❌ No matching monthly goal found")
                
                # Check what monthly goals exist
                monthly_goals = existing_goals.filter(period_type='monthly')
                print(f"   Available monthly goals:")
                for goal in monthly_goals:
                    print(f"     - '{goal.period_detail}' (id: {goal.id})")
    
    # Priority 2: Look for quarterly goals
    if days_diff <= 93:  # Less than or equal to a quarter
        quarter_num = (start_date.month - 1) // 3 + 1
        period_detail = f'Q{quarter_num}'
        print(f"\nLooking for quarterly goal with period_detail: '{period_detail}'")
        budget_goal = existing_goals.filter(
            period_type='quarter',
            period_detail=period_detail
        ).first()
        
        if budget_goal:
            print(f"✅ Found matching quarterly goal: {budget_goal}")
        else:
            print(f"❌ No matching quarterly goal found")
    
    # Priority 3: Look for annual goals
    print(f"\nLooking for annual goal")
    budget_goal = existing_goals.filter(
        period_type='annual',
        period_detail=''
    ).first()
    
    if budget_goal:
        print(f"✅ Found fallback annual goal: {budget_goal}")
    else:
        print(f"❌ No fallback annual goal found")
        
except Exception as e:
    print(f"❌ Exception occurred: {e}")
