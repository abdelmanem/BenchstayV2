from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.views import View
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone
from django.conf import settings

import json
import pandas as pd

from ..utils import parse_excel_file
from .models import GuestRequest
from django.views.generic import TemplateView
from django.db.models.functions import TruncMonth


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


class ByDepartmentReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/by_department.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)
        data = (
            qs.values('recipients')
              .annotate(total=Count('id'))
              .order_by('-total')
        )
        # open/closed counts
        rows = []
        for item in data:
            rec = item['recipients'] or 'Unknown'
            total = int(item['total'] or 0)
            open_count = qs.filter(recipients=item['recipients'], state__in=['Open','In Progress','Accepted']).count()
            closed_count = total - open_count
            rows.append({'recipients': rec, 'total': total, 'open': open_count, 'closed': closed_count})
        context['table_rows'] = rows
        context['chart_json'] = json.dumps([{'label': r['recipients'], 'count': r['total']} for r in rows])
        context['start_date'] = start_date_str or ''
        context['end_date'] = end_date_str or ''
        # Quick filter helpers
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class ByPriorityReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/by_priority.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)
        # aggregates
        priorities = (
            qs.values('priority')
              .annotate(total=Count('id'), avg_response=Avg('response_time'), avg_completion=Avg('completion_time'))
              .order_by('-total')
        )
        rows = []
        for p in priorities:
            rows.append({
                'priority': p['priority'] or 'Unknown',
                'total': int(p['total'] or 0),
                'avg_response': p['avg_response'],
                'avg_completion': p['avg_completion'],
            })
        context['table_rows'] = rows
        context['chart_json'] = json.dumps([{'label': r['priority'], 'count': r['total']} for r in rows])
        context['start_date'] = start_date_str or ''
        context['end_date'] = end_date_str or ''
        # Quick filter helpers
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class DelayedReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/delayed.html'

    DELAY_THRESHOLD = timezone.timedelta(hours=2)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)
        delayed = qs.filter(completion_time__gt=self.DELAY_THRESHOLD)
        context['threshold_hours'] = int(self.DELAY_THRESHOLD.total_seconds() // 3600)
        context['count'] = delayed.count()
        context['rows'] = delayed.values('request_id','location','priority','state','completion_time')
        context['start_date'] = start_date_str or ''
        context['end_date'] = end_date_str or ''
        # Quick filter helpers
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class MonthlySummaryReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/monthly_summary.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)
        monthly = (
            qs.annotate(month=TruncMonth('creation_date'))
              .values('month')
              .annotate(
                  total=Count('id'),
                  avg_response=Avg('response_time'),
                  avg_execution=Avg('total_duration'),
                  avg_completion=Avg('completion_time'),
              )
              .order_by('month')
        )
        rows = []
        for m in monthly:
            rows.append({
                'month': m['month'].strftime('%Y-%m') if m['month'] else '',
                'total': int(m['total'] or 0),
                'avg_response': m['avg_response'],
                'avg_execution': m['avg_execution'],
                'avg_completion': m['avg_completion'],
            })
        context['table_rows'] = rows
        context['chart_json'] = json.dumps([
            {'month': r['month'], 'total': r['total']} for r in rows
        ])
        context['start_date'] = start_date_str or ''
        context['end_date'] = end_date_str or ''
        # Quick filter helpers
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class SLAComplianceReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/sla_compliance.html'

    RESPONSE_SLA = timezone.timedelta(minutes=10)
    EXECUTION_SLA = timezone.timedelta(hours=1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters with last-month default
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)

        total = qs.count() or 1
        # Response SLA
        resp_ok = qs.filter(response_time__isnull=False, response_time__lte=self.RESPONSE_SLA).count()
        # Execution SLA (time_done - time_accepted)
        exec_ok = 0
        viol_rows = []
        for gr in qs.exclude(time_done__isnull=True).exclude(time_accepted__isnull=True).only('request_id','location','priority','response_time','time_done','time_accepted'):
            exec_time = None
            try:
                exec_time = gr.time_done - gr.time_accepted
            except Exception:
                exec_time = None
            if exec_time is not None and exec_time <= self.EXECUTION_SLA:
                exec_ok += 1
            # collect violations
            if (gr.response_time is None or gr.response_time > self.RESPONSE_SLA) or (exec_time is None or exec_time > self.EXECUTION_SLA):
                viol_rows.append({
                    'request_id': gr.request_id,
                    'location': gr.location,
                    'priority': gr.priority,
                    'response_time': gr.response_time,
                    'execution_time': exec_time,
                })

        context.update({
            'response_sla_pct': round((resp_ok / total) * 100, 2),
            'execution_sla_pct': round((exec_ok / total) * 100, 2),
            'violations': viol_rows,
            'response_sla_minutes': int(self.RESPONSE_SLA.total_seconds() // 60),
            'execution_sla_minutes': int(self.EXECUTION_SLA.total_seconds() // 60),
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
        })
        # Quick filters
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class RequestsHeatmapReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/heatmap.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters with last-month default
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)

        # Build hour x weekday matrix
        matrix = [[0 for _ in range(7)] for _ in range(24)]
        for dt in qs.values_list('creation_date', flat=True):
            if not dt:
                continue
            local = dt
            try:
                # convert to local if aware
                if timezone.is_aware(local):
                    local = timezone.localtime(local)
            except Exception:
                pass
            hour = local.hour
            weekday = local.weekday()  # 0=Mon
            matrix[hour][weekday] += 1

        context.update({
            'matrix_json': json.dumps(matrix),
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
            'hours': list(range(24)),
            'days': list(range(7)),
        })
        # Quick filters
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class TopFrequentReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/top_frequent.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters with last-month default
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)

        # Prefer type, fallback to location
        grouped = (
            qs.annotate(kind=models.Case(
                models.When(type__isnull=False, then='type'),
                default='location', output_field=models.CharField(),
            ))
        )
        # Simpler: use type or location in Python
        agg = {}
        for gr in qs.only('type','location','completion_time'):
            key = gr.type or gr.location or 'Unknown'
            entry = agg.setdefault(key, {'count':0, 'completions':[]})
            entry['count'] += 1
            if gr.completion_time:
                entry['completions'].append(gr.completion_time)
        rows = []
        for key, val in agg.items():
            avg_comp = None
            if val['completions']:
                avg_comp = sum(val['completions'], timezone.timedelta()) / len(val['completions'])
            rows.append({'type': key, 'count': val['count'], 'avg_completion': avg_comp})
        rows.sort(key=lambda x: x['count'], reverse=True)
        top10 = rows[:10]
        context.update({
            'rows': top10,
            'chart_json': json.dumps([{'label': r['type'], 'count': r['count']} for r in top10]),
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
        })
        # Quick filters
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class DepartmentPerformanceReportView(TemplateView):
    template_name = 'hotelkit/guest_requests/reports/department_performance.html'

    RESPONSE_SLA = timezone.timedelta(minutes=10)
    EXECUTION_SLA = timezone.timedelta(hours=1)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()
        # Date filters with last-month default
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()
        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)

        # Aggregate per department (recipients)
        departments = {}
        for gr in qs.only('recipients','response_time','time_done','time_accepted'):
            dept = (gr.recipients or 'Unknown').split(',')[0].strip() if gr.recipients else 'Unknown'
            item = departments.setdefault(dept, {
                'total': 0, 'responses': [], 'execs': [], 'sla_hits': 0
            })
            item['total'] += 1
            if gr.response_time:
                item['responses'].append(gr.response_time)
            exec_time = None
            if gr.time_done and gr.time_accepted:
                exec_time = gr.time_done - gr.time_accepted
                item['execs'].append(exec_time)
            # SLA compliance: both response and execution must meet thresholds when present
            resp_ok = (gr.response_time is not None and gr.response_time <= self.RESPONSE_SLA)
            exec_ok = (exec_time is not None and exec_time <= self.EXECUTION_SLA)
            if resp_ok and exec_ok:
                item['sla_hits'] += 1

        rows = []
        for dept, val in departments.items():
            avg_resp = sum(val['responses'], timezone.timedelta()) / len(val['responses']) if val['responses'] else None
            avg_exec = sum(val['execs'], timezone.timedelta()) / len(val['execs']) if val['execs'] else None
            sla_pct = round((val['sla_hits'] / val['total']) * 100, 2) if val['total'] else 0
            rows.append({'dept': dept, 'total': val['total'], 'avg_response': avg_resp, 'avg_execution': avg_exec, 'sla_pct': sla_pct})
        rows.sort(key=lambda x: x['total'], reverse=True)

        context.update({
            'rows': rows,
            'chart_json': json.dumps([
                {'label': r['dept'], 'total': r['total'], 'sla_pct': r['sla_pct']}
                for r in rows
            ]),
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
        })
        # Quick filters
        today = timezone.now().date()
        first_of_current = today.replace(day=1)
        last7 = (today - timezone.timedelta(days=6))
        last30 = (today - timezone.timedelta(days=29))
        last_month_end = first_of_current - timezone.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        context.update({
            'qf_today': today.isoformat(),
            'qf_this_month_start': first_of_current.isoformat(),
            'qf_last7_start': last7.isoformat(),
            'qf_last30_start': last30.isoformat(),
            'qf_last_month_start': last_month_start.isoformat(),
            'qf_last_month_end': last_month_end.isoformat(),
        })
        return context


class GuestRequestsByTypeView(TemplateView):
    template_name = 'hotelkit/guest_requests/guest_requests_by_type.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = GuestRequest.objects.all()

        # Filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        status = self.request.GET.get('status') or ''
        request_type = self.request.GET.get('type') or ''

        if not start_date_str and not end_date_str:
            today = timezone.now().date()
            first_of_current = today.replace(day=1)
            last_month_end = first_of_current - timezone.timedelta(days=1)
            last_month_start = last_month_end.replace(day=1)
            start_date_str = last_month_start.isoformat()
            end_date_str = last_month_end.isoformat()

        start_date = pd.to_datetime(start_date_str, errors='coerce').date() if start_date_str else None
        end_date = pd.to_datetime(end_date_str, errors='coerce').date() if end_date_str else None
        if start_date:
            qs = qs.filter(creation_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(creation_date__date__lte=end_date)
        if status:
            qs = qs.filter(state=status)
        if request_type:
            qs = qs.filter(type=request_type)

        # Available types for filter
        available_types = list(
            qs.exclude(type__isnull=True).exclude(type='').values_list('type', flat=True).distinct().order_by('type')
        )

        # Group by type
        grouped = {}
        for gr in qs.order_by('-creation_date'):
            key = gr.type or 'Unknown'
            bucket = grouped.setdefault(key, {'items': [], 'response': [], 'completion': []})
            bucket['items'].append(gr)
            if gr.response_time:
                bucket['response'].append(gr.response_time)
            if gr.completion_time:
                bucket['completion'].append(gr.completion_time)

        # Build a convenient structure for template
        by_type = {}
        for key, data in grouped.items():
            avg_response = sum(data['response'], timezone.timedelta()) / len(data['response']) if data['response'] else None
            avg_completion = sum(data['completion'], timezone.timedelta()) / len(data['completion']) if data['completion'] else None
            # attach aggregate to first item for display like repairs page
            items = data['items']
            if items:
                items[0].avg_response_time = avg_response
                items[0].avg_completion_time = avg_completion
            by_type[key] = items

        context.update({
            'guest_requests_by_type': by_type,
            'available_types': available_types,
            'start_date': start_date_str or '',
            'end_date': end_date_str or '',
            'status': status,
            'request_type': request_type,
        })
        return context


