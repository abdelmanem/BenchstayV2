from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views import View
from django.db.models import Avg, Count
from django.utils import timezone
from django.conf import settings

import json
import pandas as pd

from ..utils import parse_excel_file
from .models import GuestRequest


def format_duration_td(td):
    if not td:
        return 'N/A'
    total_seconds = int(td.total_seconds())
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{seconds}s")
    return ' '.join(parts)


class UploadView(View):
    template_name = 'hotelkit/guest_requests/upload.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            messages.error(request, 'Please select an Excel file to upload.')
            return redirect(reverse('guest_requests:upload'))

        try:
            df = parse_excel_file(file)
        except Exception as e:
            messages.error(request, str(e))
            return redirect(reverse('guest_requests:upload'))

        # Column mapping (handle both raw export headers and hotelkit.utils renames)
        COLS = {
            'ID': 'request_id',
            'id_field': 'request_id',  # when parse_excel_file already renamed
            'Creator': 'creator',
            'Recipients': 'recipients',
            'Location': 'location',
            'Type': 'type',
            'Creation date': 'creation_date',
            'Priority': 'priority',
            'State': 'state',
            'Time accepted': 'time_accepted',
            'Time done': 'time_done',
        }

        # Normalize columns
        df = df.rename(columns={k: v for k, v in COLS.items() if k in df.columns})

        # Ensure datetime parsing
        for col in ['creation_date', 'time_accepted', 'time_done']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        def normalize_dt(value):
            if value is None:
                return None
            # Treat pandas NaT/NaN as None
            if isinstance(value, pd._libs.tslibs.nattype.NaTType) or pd.isna(value):
                return None
            # If it's a pandas Timestamp, convert to python datetime
            if isinstance(value, pd.Timestamp):
                if value is pd.NaT:
                    return None
                value = value.to_pydatetime()
            # If still a string, try parse
            if isinstance(value, str) and value.strip():
                ts = pd.to_datetime(value, errors='coerce')
                if ts is pd.NaT or pd.isna(ts):
                    return None
                value = ts.to_pydatetime()
            # Ensure timezone awareness if USE_TZ
            try:
                if value and getattr(settings, 'USE_TZ', False) and getattr(value, 'tzinfo', None) is None:
                    return timezone.make_aware(value)
            except Exception:
                pass
            return value

        imported = 0
        skipped = 0
        for _, row in df.iterrows():
            request_id = row.get('request_id') or row.get('ID') or row.get('id_field')
            if not request_id:
                skipped += 1
                continue

            if GuestRequest.objects.filter(request_id=request_id).exists():
                skipped += 1
                continue

            # Normalize and coerce datetimes and strings
            gr = GuestRequest(
                request_id=str(request_id),
                creator=str(row.get('creator') or row.get('Creator') or ''),
                recipients=str(row.get('recipients') or row.get('Recipients') or ''),
                location=row.get('location') or row.get('Location') or None,
                type=row.get('type') or row.get('Type') or None,
                creation_date=normalize_dt(row.get('creation_date') or row.get('Creation date')),
                priority=row.get('priority') or row.get('Priority') or None,
                state=row.get('state') or row.get('State') or None,
                time_accepted=normalize_dt(row.get('time_accepted') or row.get('Time accepted')),
                time_done=normalize_dt(row.get('time_done') or row.get('Time done')),
            )
            gr.save()
            imported += 1

        messages.success(request, f"Upload completed: {imported} imported, {skipped} skipped")
        return redirect(reverse('guest_requests:dashboard'))


class DashboardView(View):
    template_name = 'hotelkit/guest_requests/guest_requests_dashboard.html'

    def get(self, request):
        qs = GuestRequest.objects.all()

        # Optional date filters
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')

        # Default to last month if no dates provided
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = pd.to_datetime(start_date_str, errors='coerce').date()
            except Exception:
                start_date = None
        if end_date_str:
            try:
                end_date = pd.to_datetime(end_date_str, errors='coerce').date()
            except Exception:
                end_date = None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)

        total_requests = qs.count()
        open_requests = qs.filter(state__in=['Open', 'In Progress', 'Accepted']).count()

        avg_response = qs.aggregate(avg=Avg('response_time'))['avg']
        avg_completion = qs.aggregate(avg=Avg('completion_time'))['avg']
        avg_execution = qs.aggregate(avg=Avg('total_duration'))['avg']

        # Trends
        from django.db.models.functions import TruncDate
        created_trend = (
            qs.annotate(day=TruncDate('creation_date'))
              .values('day')
              .annotate(count=Count('id'))
              .order_by('day')
        )
        completed_trend = (
            qs.exclude(time_done__isnull=True)
              .annotate(day=TruncDate('time_done'))
              .values('day')
              .annotate(count=Count('id'))
              .order_by('day')
        )
        # Serialize trends to JSON-friendly data
        created_trend_json = [
            {
                'day': (item['day'].isoformat() if item['day'] else None),
                'count': int(item['count'] or 0),
            }
            for item in created_trend
        ]
        completed_trend_json = [
            {
                'day': (item['day'].isoformat() if item['day'] else None),
                'count': int(item['count'] or 0),
            }
            for item in completed_trend
        ]

        # Pie by recipients (department)
        # Build department counts by splitting comma-separated recipients
        recipient_counts = {}
        for rec in qs.exclude(recipients__isnull=True).exclude(recipients='').values_list('recipients', flat=True):
            parts = [p.strip() for p in str(rec).split(',') if p and p.strip()]
            if not parts:
                continue
            # Use first recipient as department key
            key = parts[0]
            recipient_counts[key] = recipient_counts.get(key, 0) + 1
        # Convert to sorted list
        by_recipients_json = [
            {'recipients': k, 'count': v} for k, v in sorted(recipient_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        # Bar by priority
        by_priority = (
            qs.exclude(priority__isnull=True).exclude(priority='')
              .values('priority')
              .annotate(count=Count('id'))
              .order_by('-count')
        )
        by_priority_json = [
            {'priority': item['priority'] or 'Unknown', 'count': int(item['count'] or 0)}
            for item in by_priority
        ]

        # By type distribution
        by_type = (
            qs.exclude(type__isnull=True).exclude(type='')
              .values('type')
              .annotate(count=Count('id'))
              .order_by('-count')
        )
        by_type_json = [
            {'type': item['type'] or 'Unknown', 'count': int(item['count'] or 0)}
            for item in by_type
        ]

        latest = qs.order_by('-creation_date')[:10]

        context = {
            'total_requests': total_requests,
            'open_requests': open_requests,
            'avg_response': format_duration_td(avg_response),
            'avg_completion': format_duration_td(avg_completion),
            'avg_execution': format_duration_td(avg_execution),
            'created_trend_json': json.dumps(created_trend_json),
            'completed_trend_json': json.dumps(completed_trend_json),
            'by_recipients_json': json.dumps(by_recipients_json),
            'by_priority_json': json.dumps(by_priority_json),
            'by_type_json': json.dumps(by_type_json),
            'latest': latest,
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
        }

        return render(request, self.template_name, context)


