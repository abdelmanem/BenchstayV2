import pandas as pd
from datetime import datetime
from django.utils import timezone
from .models import RepairRequest


def parse_excel_file(file_path):
    """
    Parse Excel file and return DataFrame with proper column mapping.
    """
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Map column names to model fields
        column_mapping = {
            'Position': 'position',
            'ID': 'id_field',
            'Creator': 'creator',
            'Recipients': 'recipients',
            'Location': 'location',
            'Location path': 'location_path',
            'Type': 'type',
            'Type path': 'type_path',
            'Assets': 'assets',
            'Ticket': 'ticket',
            'Creation date': 'creation_date',
            'Priority': 'priority',
            'State': 'state',
            'Latest state change user': 'latest_state_change_user',
            'Latest state change time': 'latest_state_change_time',
            'Time accepted': 'time_accepted',
            'Time in progress': 'time_in_progress',
            'Time done': 'time_done',
            'Time "in evaluation"': 'time_in_evaluation',
            'Text': 'text',
            'Link': 'link',
            'Submitted result': 'submitted_result',
            'Comments': 'comments',
            'Parking reason': 'parking_reason',
            'Parking information': 'parking_information',
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Convert datetime columns
        datetime_columns = [
            'creation_date', 'latest_state_change_time', 'time_accepted',
            'time_in_progress', 'time_done', 'time_in_evaluation'
        ]
        
        for col in datetime_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
        
    except Exception as e:
        raise Exception(f"Error parsing Excel file: {str(e)}")


def import_repair_requests_from_dataframe(df):
    """
    Import repair requests from DataFrame.
    Updates existing records if ID already exists.
    """
    imported_count = 0
    updated_count = 0
    errors = []
    
    for index, row in df.iterrows():
        try:
            # Prepare data for model
            data = row.to_dict()
            
            # Remove NaN values and convert to None
            for key, value in data.items():
                if pd.isna(value):
                    data[key] = None
            
            # Get or create the repair request
            repair_request, created = RepairRequest.objects.get_or_create(
                id_field=data['id_field'],
                defaults=data
            )
            
            if not created:
                # Update existing record
                for field, value in data.items():
                    if field != 'id_field':  # Don't update the ID field
                        setattr(repair_request, field, value)
                repair_request.save()
                updated_count += 1
            else:
                imported_count += 1
                
        except Exception as e:
            errors.append(f"Row {index + 1}: {str(e)}")
    
    return {
        'imported': imported_count,
        'updated': updated_count,
        'errors': errors
    }


def create_excel_template():
    """
    Create an Excel template with the correct column headers.
    """
    template_data = {
        'Position': [1],
        'ID': ['REQ-001'],
        'Creator': ['John Doe'],
        'Recipients': ['Technician A'],
        'Location': ['Room 101'],
        'Location path': ['Building A / Floor 1 / Room 101'],
        'Type': ['Plumbing'],
        'Type path': ['Maintenance / Plumbing'],
        'Assets': ['Sink, Faucet'],
        'Ticket': ['TKT-001'],
        'Creation date': [datetime.now()],
        'Priority': ['High'],
        'State': ['Open'],
        'Latest state change user': ['John Doe'],
        'Latest state change time': [datetime.now()],
        'Time accepted': [None],
        'Time in progress': [None],
        'Time done': [None],
        'Time "in evaluation"': [None],
        'Text': ['Sink is leaking'],
        'Link': ['https://example.com'],
        'Submitted result': [None],
        'Comments': [None],
        'Parking reason': [None],
        'Parking information': [None],
    }
    
    df = pd.DataFrame(template_data)
    return df


def get_repair_kpis(start_date=None, end_date=None):
    """
    Calculate KPIs for repair requests.
    """
    queryset = RepairRequest.objects.all()
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    # Calculate average response time
    response_times = queryset.exclude(response_time__isnull=True).values_list('response_time', flat=True)
    if response_times:
        total_response_time = sum(response_times, timezone.timedelta())
        avg_response_time = total_response_time / len(response_times)
    else:
        avg_response_time = None
    
    # Calculate average completion time
    completion_times = queryset.exclude(completion_time__isnull=True).values_list('completion_time', flat=True)
    if completion_times:
        total_completion_time = sum(completion_times, timezone.timedelta())
        avg_completion_time = total_completion_time / len(completion_times)
    else:
        avg_completion_time = None
    
    # Calculate average execution time
    execution_times = queryset.exclude(execution_time__isnull=True).values_list('execution_time', flat=True)
    if execution_times:
        total_execution_time = sum(execution_times, timezone.timedelta())
        avg_execution_time = total_execution_time / len(execution_times)
    else:
        avg_execution_time = None
    
    # Count open requests
    open_requests = queryset.filter(state__in=['Open', 'In Progress', 'Accepted', 'In Evaluation']).count()
    
    return {
        'avg_response_time': avg_response_time,
        'avg_completion_time': avg_completion_time,
        'avg_execution_time': avg_execution_time,
        'open_requests': open_requests
    }


def get_repair_trends(start_date=None, end_date=None):
    """
    Get daily trends for repair requests.
    """
    from django.db import models
    
    queryset = RepairRequest.objects.all()
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    # Get created counts by date
    created_data = queryset.extra(
        select={'date': 'DATE(creation_date)'}
    ).values('date').annotate(
        created_count=models.Count('id')
    ).order_by('date')
    
    # Get closed counts by date
    closed_data = queryset.filter(
        state__in=['Closed', 'Done', 'Completed', 'Resolved']
    ).extra(
        select={'date': 'DATE(time_done)'}
    ).values('date').annotate(
        closed_count=models.Count('id')
    ).order_by('date')
    
    # Merge the data
    trend_data = {}
    for item in created_data:
        trend_data[item['date']] = {
            'date': item['date'],
            'created_count': item['created_count'],
            'closed_count': 0
        }
    
    for item in closed_data:
        if item['date'] in trend_data:
            trend_data[item['date']]['closed_count'] = item['closed_count']
        else:
            trend_data[item['date']] = {
                'date': item['date'],
                'created_count': 0,
                'closed_count': item['closed_count']
            }
    
    return list(trend_data.values())


def get_repair_types(start_date=None, end_date=None):
    """
    Get distribution of repair requests by type.
    """
    from django.db import models
    
    queryset = RepairRequest.objects.all()
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    type_data = queryset.values('type').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    total_count = sum(item['count'] for item in type_data)
    
    result = []
    for item in type_data:
        percentage = (item['count'] / total_count * 100) if total_count > 0 else 0
        result.append({
            'type': item['type'],
            'count': item['count'],
            'percentage': round(percentage, 2)
        })
    
    return result


def get_repair_heatmap(start_date=None, end_date=None):
    """
    Get heatmap data for repair requests by location.
    """
    from django.db import models
    
    queryset = RepairRequest.objects.all()
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    heatmap_data = queryset.values('location').annotate(
        count=models.Count('id')
    ).order_by('-count')
    
    result = []
    for item in heatmap_data:
        # Extract floor information if available
        floor = None
        if 'floor' in item['location'].lower():
            floor = item['location'].split()[0] if item['location'].split() else None
        
        result.append({
            'location': item['location'],
            'count': item['count'],
            'floor': floor
        })
    
    return result


def get_top_rooms(start_date=None, end_date=None, limit=5):
    """
    Get top rooms by repair request count.
    """
    from django.db import models
    
    queryset = RepairRequest.objects.all()
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    top_rooms = queryset.values('location').annotate(
        count=models.Count('id'),
        avg_completion_time=models.Avg('completion_time')
    ).order_by('-count')[:limit]
    
    return list(top_rooms)


def get_technician_performance(start_date=None, end_date=None):
    """
    Get technician performance data.
    """
    from django.db import models
    
    queryset = RepairRequest.objects.exclude(recipients__isnull=True).exclude(recipients='')
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    tech_data = queryset.values('recipients').annotate(
        count=models.Count('id'),
        avg_response_time=models.Avg('response_time'),
        avg_completion_time=models.Avg('completion_time')
    ).order_by('-count')
    
    return list(tech_data)


def get_sla_compliance(start_date=None, end_date=None):
    """
    Get SLA compliance rates.
    """
    from django.db import models
    
    queryset = RepairRequest.objects.filter(
        state__in=['Closed', 'Done', 'Completed', 'Resolved']
    ).exclude(completion_time__isnull=True)
    
    if start_date:
        queryset = queryset.filter(creation_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(creation_date__lte=end_date)
    
    total_count = queryset.count()
    
    if total_count == 0:
        return []
    
    # 4-hour SLA
    compliant_4h = queryset.filter(completion_time__lte=timezone.timedelta(hours=4)).count()
    
    # 24-hour SLA
    compliant_24h = queryset.filter(completion_time__lte=timezone.timedelta(hours=24)).count()
    
    # 48-hour SLA
    compliant_48h = queryset.filter(completion_time__lte=timezone.timedelta(hours=48)).count()
    
    return [
        {
            'sla_period': '4 hours',
            'compliant_count': compliant_4h,
            'total_count': total_count,
            'compliance_rate': round((compliant_4h / total_count) * 100, 2)
        },
        {
            'sla_period': '24 hours',
            'compliant_count': compliant_24h,
            'total_count': total_count,
            'compliance_rate': round((compliant_24h / total_count) * 100, 2)
        },
        {
            'sla_period': '48 hours',
            'compliant_count': compliant_48h,
            'total_count': total_count,
            'compliance_rate': round((compliant_48h / total_count) * 100, 2)
        }
    ]
