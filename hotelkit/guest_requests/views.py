from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views import View
from django.db.models import Avg, Count
from django.utils import timezone
from django.conf import settings

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

        # Pie by recipients (department)
        by_recipients = (
            qs.exclude(recipients__isnull=True).exclude(recipients='')
              .values('recipients')
              .annotate(count=Count('id'))
              .order_by('-count')
        )

        # Bar by priority
        by_priority = (
            qs.exclude(priority__isnull=True).exclude(priority='')
              .values('priority')
              .annotate(count=Count('id'))
              .order_by('-count')
        )

        latest = qs.order_by('-creation_date')[:10]

        context = {
            'total_requests': total_requests,
            'open_requests': open_requests,
            'avg_response': format_duration_td(avg_response),
            'avg_completion': format_duration_td(avg_completion),
            'avg_execution': format_duration_td(avg_execution),
            'created_trend': list(created_trend),
            'completed_trend': list(completed_trend),
            'by_recipients': list(by_recipients),
            'by_priority': list(by_priority),
            'latest': latest,
        }

        return render(request, self.template_name, context)


