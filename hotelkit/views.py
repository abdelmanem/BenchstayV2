from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from datetime import datetime, timedelta
import pandas as pd
import io
import json
from datetime import date, datetime

from .models import RepairRequest
from .serializers import (
    RepairRequestSerializer, RepairRequestKPISerializer,
    RepairRequestTrendSerializer, RepairRequestTypeSerializer,
    RepairRequestHeatmapSerializer, RepairRequestTopRoomsSerializer,
    RepairRequestTechnicianSerializer, RepairRequestSLASerializer
)
from .utils import (
    parse_excel_file, import_repair_requests_from_dataframe,
    create_excel_template, get_repair_kpis, get_repair_trends,
    get_repair_types, get_repair_heatmap, get_top_rooms,
    get_technician_performance, get_sla_compliance,
    # Advanced reporting functions
    get_sla_compliance_advanced, get_delay_by_priority, get_escalations,
    get_technician_performance_advanced, get_reopened_requests,
    get_workload_distribution, get_top_assets, get_repeat_requests,
    get_bottlenecks, get_avg_evaluation_time, get_parking_reasons,
    get_guest_facing_requests, get_internal_requests,
    # Export functions
    export_to_excel, export_to_pdf
)


def json_serializer(obj):
    """Custom JSON serializer for date and datetime objects."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class RepairRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for RepairRequest model."""
    queryset = RepairRequest.objects.all()
    serializer_class = RepairRequestSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['state', 'priority', 'type', 'location', 'creator']
    search_fields = ['id_field', 'location', 'type', 'creator', 'text']
    ordering_fields = ['creation_date', 'completion_time', 'response_time']
    ordering = ['-creation_date']
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """Get KPIs for repair requests."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        kpis = get_repair_kpis(start_date, end_date)
        serializer = RepairRequestKPISerializer(kpis)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def trend(self, request):
        """Get trend data for repair requests."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        trends = get_repair_trends(start_date, end_date)
        serializer = RepairRequestTrendSerializer(trends, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get type distribution for repair requests."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        types = get_repair_types(start_date, end_date)
        serializer = RepairRequestTypeSerializer(types, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def heatmap(self, request):
        """Get heatmap data for repair requests."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        heatmap = get_repair_heatmap(start_date, end_date)
        serializer = RepairRequestHeatmapSerializer(heatmap, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_rooms(self, request):
        """Get top rooms by repair request count."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 5))
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        top_rooms = get_top_rooms(start_date, end_date, limit)
        serializer = RepairRequestTopRoomsSerializer(top_rooms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def technicians(self, request):
        """Get technician performance data."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        technicians = get_technician_performance(start_date, end_date)
        serializer = RepairRequestTechnicianSerializer(technicians, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def sla(self, request):
        """Get SLA compliance data."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        sla_data = get_sla_compliance(start_date, end_date)
        serializer = RepairRequestSLASerializer(sla_data, many=True)
        return Response(serializer.data)

    # Advanced Reporting Endpoints
    @action(detail=False, methods=['get'])
    def sla_compliance(self, request):
        """Get advanced SLA compliance data."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        sla_data = get_sla_compliance_advanced(start_date, end_date)
        return Response(sla_data)

    @action(detail=False, methods=['get'])
    def delay_by_priority(self, request):
        """Get average response/completion time grouped by priority."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        delay_data = get_delay_by_priority(start_date, end_date)
        return Response(delay_data)

    @action(detail=False, methods=['get'])
    def escalations(self, request):
        """Get count of requests with changed recipients."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        escalation_data = get_escalations(start_date, end_date)
        return Response(escalation_data)

    @action(detail=False, methods=['get'])
    def technician_performance(self, request):
        """Get advanced technician performance data."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        performance_data = get_technician_performance_advanced(start_date, end_date)
        return Response(performance_data)

    @action(detail=False, methods=['get'])
    def reopened(self, request):
        """Get requests closed then reopened."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        reopened_data = get_reopened_requests(start_date, end_date)
        return Response(reopened_data)

    @action(detail=False, methods=['get'])
    def workload_distribution(self, request):
        """Get current open requests per technician."""
        workload_data = get_workload_distribution()
        return Response(workload_data)

    @action(detail=False, methods=['get'])
    def top_rooms(self, request):
        """Get top rooms by repair request count."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 5))
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        top_rooms = get_top_rooms(start_date, end_date, limit)
        serializer = RepairRequestTopRoomsSerializer(top_rooms, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_assets(self, request):
        """Get top assets by repair request count."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 5))
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        top_assets = get_top_assets(start_date, end_date, limit)
        return Response(top_assets)

    @action(detail=False, methods=['get'])
    def repeat_requests(self, request):
        """Get repeat requests for same location/type."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        repeat_data = get_repeat_requests(start_date, end_date)
        return Response(repeat_data)

    @action(detail=False, methods=['get'])
    def bottlenecks(self, request):
        """Get process bottlenecks analysis."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        bottleneck_data = get_bottlenecks(start_date, end_date)
        return Response(bottleneck_data)

    @action(detail=False, methods=['get'])
    def avg_evaluation_time(self, request):
        """Get average evaluation time."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        eval_data = get_avg_evaluation_time(start_date, end_date)
        return Response(eval_data)

    @action(detail=False, methods=['get'])
    def parking_reasons(self, request):
        """Get parking reasons analysis."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        parking_data = get_parking_reasons(start_date, end_date)
        return Response(parking_data)

    @action(detail=False, methods=['get'])
    def guest_facing(self, request):
        """Get guest-facing requests analysis."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        guest_data = get_guest_facing_requests(start_date, end_date)
        return Response(guest_data)

    @action(detail=False, methods=['get'])
    def internal(self, request):
        """Get internal requests analysis."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        internal_data = get_internal_requests(start_date, end_date)
        return Response(internal_data)


class RepairImportView(APIView):
    """View for importing repair requests from Excel/CSV files."""
    
    def post(self, request):
        """Import repair requests from uploaded file."""
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file uploaded'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file = request.FILES['file']
        
        try:
            # Parse the file
            if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                df = parse_excel_file(file)
            else:
                return Response(
                    {'error': 'Only Excel files (.xlsx, .xls) are supported'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Import the data
            result = import_repair_requests_from_dataframe(df)
            
            return Response({
                'message': 'Import completed successfully',
                'imported': result['imported'],
                'updated': result['updated'],
                'errors': result['errors']
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class RepairTemplateView(APIView):
    """View for downloading Excel template."""
    
    def get(self, request):
        """Download Excel template."""
        try:
            # Create template DataFrame
            df = create_excel_template()
            
            # Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Repair Requests Template', index=False)
            
            output.seek(0)
            
            # Create HTTP response
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="repair_requests_template.xlsx"'
            
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RepairsDashboardView(PermissionRequiredMixin, TemplateView):
    """Dashboard view for repairs analytics."""
    template_name = 'hotelkit/repairs_dashboard.html'
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date filters from query parameters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        # Parse dates
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # If no dates provided, default to last month
        if not start_date and not end_date:
            from datetime import date
            import calendar
            today = date.today()
            
            # Calculate first day of last month
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
            else:
                start_date = date(today.year, today.month - 1, 1)
            
            # Calculate last day of last month
            if today.month == 1:
                end_date = date(today.year - 1, 12, 31)
            else:
                # Get last day of previous month
                last_day = calendar.monthrange(today.year, today.month - 1)[1]
                end_date = date(today.year, today.month - 1, last_day)
        
        # Get KPIs
        kpis = get_repair_kpis(start_date, end_date)
        context['kpis'] = kpis
        
        # Get trends
        trends = get_repair_trends(start_date, end_date)
        context['trends'] = json.dumps(trends, default=json_serializer)
        
        # Get types
        types = get_repair_types(start_date, end_date)
        context['types'] = json.dumps(types, default=json_serializer)
        
        # Get heatmap
        heatmap = get_repair_heatmap(start_date, end_date)
        context['heatmap'] = json.dumps(heatmap, default=json_serializer)
        
        # Get top rooms
        top_rooms = get_top_rooms(start_date, end_date)
        context['top_rooms'] = top_rooms
        
        # Get technicians
        technicians = get_technician_performance(start_date, end_date)
        context['technicians'] = technicians
        
        # Get SLA compliance
        sla_data = get_sla_compliance(start_date, end_date)
        context['sla_data'] = json.dumps(sla_data, default=json_serializer)
        
        # Date filters for template
        context['start_date'] = start_date.strftime('%Y-%m-%d') if start_date else ''
        context['end_date'] = end_date.strftime('%Y-%m-%d') if end_date else ''
        
        return context


class RepairsByTypeView(PermissionRequiredMixin, ListView):
    """View to display all repairs organized by type."""
    model = RepairRequest
    template_name = 'hotelkit/repairs_by_type.html'
    context_object_name = 'repairs_by_type'
    paginate_by = 50
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def get_queryset(self):
        """Get repairs filtered by date and status."""
        queryset = RepairRequest.objects.all()
        
        # Date filters
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(creation_date__date__gte=start_date)
            except ValueError:
                pass
                
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(creation_date__date__lte=end_date)
            except ValueError:
                pass
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(state=status)
        
        # Type filter
        repair_type = self.request.GET.get('type')
        if repair_type:
            queryset = queryset.filter(type=repair_type)
        
        # If no filters, default to last month
        if not start_date and not end_date and not status and not repair_type:
            from datetime import date
            import calendar
            today = date.today()
            
            # Calculate first day of last month
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
            else:
                start_date = date(today.year, today.month - 1, 1)
            
            # Calculate last day of last month
            if today.month == 1:
                end_date = date(today.year - 1, 12, 31)
            else:
                last_day = calendar.monthrange(today.year, today.month - 1)[1]
                end_date = date(today.year, today.month - 1, last_day)
            
            queryset = queryset.filter(creation_date__date__gte=start_date, creation_date__date__lte=end_date)
        
        return queryset.order_by('type', '-creation_date')
    
    def get_context_data(self, **kwargs):
        """Organize repairs by type and add pagination."""
        context = super().get_context_data(**kwargs)
        
        # Get all repairs (not paginated for grouping)
        all_repairs = self.get_queryset()
        
        # Group repairs by type
        repairs_by_type = {}
        for repair in all_repairs:
            type_name = repair.type or 'Uncategorized'
            if type_name not in repairs_by_type:
                repairs_by_type[type_name] = []
            repairs_by_type[type_name].append(repair)
        
        # Calculate stats for each type
        for type_name, repairs in repairs_by_type.items():
            if repairs:
                # Calculate average response time for this type
                response_times = [r.response_time for r in repairs if r.response_time]
                if response_times:
                    avg_response = sum(response_times, timedelta()) / len(response_times)
                else:
                    avg_response = None
                
                # Calculate average completion time for this type
                completion_times = [r.completion_time for r in repairs if r.completion_time]
                if completion_times:
                    avg_completion = sum(completion_times, timedelta()) / len(completion_times)
                else:
                    avg_completion = None
                
                # Add stats to first repair in the list for template access
                repairs[0].avg_response_time = avg_response
                repairs[0].avg_completion_time = avg_completion
        
        context['repairs_by_type'] = repairs_by_type
        
        # Get available types for filter dropdown
        available_types = RepairRequest.objects.values_list('type', flat=True).distinct().exclude(type__isnull=True).exclude(type='').order_by('type')
        context['available_types'] = available_types
        
        # Add filter values for template - check if we have default dates
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if not start_date_str and not end_date_str:
            # Set default dates to last month
            from datetime import date
            import calendar
            today = date.today()
            
            if today.month == 1:
                default_start = date(today.year - 1, 12, 1)
                default_end = date(today.year - 1, 12, 31)
            else:
                default_start = date(today.year, today.month - 1, 1)
                last_day = calendar.monthrange(today.year, today.month - 1)[1]
                default_end = date(today.year, today.month - 1, last_day)
            
            context['start_date'] = default_start.strftime('%Y-%m-%d')
            context['end_date'] = default_end.strftime('%Y-%m-%d')
        else:
            context['start_date'] = start_date_str or ''
            context['end_date'] = end_date_str or ''
        
        context['status'] = self.request.GET.get('status', '')
        context['repair_type'] = self.request.GET.get('type', '')
        
        return context


class RepairDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """View for displaying repair request details."""
    model = RepairRequest
    template_name = 'hotelkit/repair_detail.html'
    context_object_name = 'repair'
    pk_url_kwarg = 'id'
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True


class RepairUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """View for editing repair requests."""
    model = RepairRequest
    template_name = 'hotelkit/repair_edit.html'
    fields = ['state', 'priority', 'recipients', 'text', 'comments']
    pk_url_kwarg = 'id'
    context_object_name = 'repair'
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def get_success_url(self):
        return reverse_lazy('repairs:repairs_by_type')
    
    def form_valid(self, form):
        messages.success(self.request, f'Repair request #{self.object.id} updated successfully.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure the repair object is available in the template
        context['repair'] = self.get_object()
        return context


class RepairDeleteView(LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, DeleteView):
    """View for deleting repair requests (admin/superuser only)."""
    model = RepairRequest
    template_name = 'hotelkit/repair_confirm_delete.html'
    pk_url_kwarg = 'id'
    context_object_name = 'repair'
    success_url = reverse_lazy('repairs:repairs_by_type')
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def test_func(self):
        """Only admin or superuser can delete repair requests."""
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ensure the repair object is available in the template
        context['repair'] = self.get_object()
        return context
    
    def delete(self, request, *args, **kwargs):
        repair_id = self.get_object().id
        messages.success(request, f'Repair request #{repair_id} deleted successfully.')
        return super().delete(request, *args, **kwargs)


def repairs_import_view(request):
    """Simple import view for form-based uploads."""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'No file uploaded')
            return redirect('repairs:repairs_dashboard')
        
        file = request.FILES['file']
        
        try:
            # Parse the file
            if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                df = parse_excel_file(file)
            else:
                messages.error(request, 'Only Excel files (.xlsx, .xls) are supported')
                return redirect('repairs:repairs_dashboard')
            
            # Import the data
            result = import_repair_requests_from_dataframe(df)
            
            messages.success(
                request, 
                f'Import completed: {result["imported"]} imported, {result["updated"]} updated'
            )
            
            if result['errors']:
                for error in result['errors'][:5]:  # Show first 5 errors
                    messages.warning(request, error)
            
        except Exception as e:
            messages.error(request, f'Import failed: {str(e)}')
    
    return redirect('repairs:repairs_dashboard')


# Report Views
class DailyFlashReportView(PermissionRequiredMixin, TemplateView):
    """Daily Flash Report view."""
    template_name = 'hotelkit/reports/daily_flash_report.html'
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Default to today if no dates provided
        if not start_date and not end_date:
            from datetime import date
            today = date.today()
            start_date = today
            end_date = today
        
        context['start_date'] = start_date.strftime('%Y-%m-%d') if start_date else ''
        context['end_date'] = end_date.strftime('%Y-%m-%d') if end_date else ''
        
        return context


class WeeklyTrendReportView(PermissionRequiredMixin, TemplateView):
    """Weekly Trend Report view."""
    template_name = 'hotelkit/reports/weekly_trend_report.html'
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Default to last week if no dates provided
        if not start_date and not end_date:
            from datetime import date, timedelta
            today = date.today()
            start_date = today - timedelta(days=7)
            end_date = today
        
        context['start_date'] = start_date.strftime('%Y-%m-%d') if start_date else ''
        context['end_date'] = end_date.strftime('%Y-%m-%d') if end_date else ''
        
        return context


class MonthlyRootCauseReportView(PermissionRequiredMixin, TemplateView):
    """Monthly Root Cause Report view."""
    template_name = 'hotelkit/reports/monthly_root_cause_report.html'
    permission_required = 'accounts.view_hotelkit'
    raise_exception = True
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get date filters
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Default to last month if no dates provided
        if not start_date and not end_date:
            from datetime import date
            import calendar
            today = date.today()
            
            if today.month == 1:
                start_date = date(today.year - 1, 12, 1)
                end_date = date(today.year - 1, 12, 31)
            else:
                start_date = date(today.year, today.month - 1, 1)
                last_day = calendar.monthrange(today.year, today.month - 1)[1]
                end_date = date(today.year, today.month - 1, last_day)
        
        context['start_date'] = start_date.strftime('%Y-%m-%d') if start_date else ''
        context['end_date'] = end_date.strftime('%Y-%m-%d') if end_date else ''
        
        return context


# Export Views
class ExportExcelView(APIView):
    """Export reports to Excel."""
    
    def get(self, request):
        report_type = request.GET.get('type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not report_type:
            return Response({'error': 'Report type is required'}, status=400)
        
        # Parse dates
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        try:
            # Generate Excel file
            excel_file = export_to_excel(report_type, start_date_obj, end_date_obj)
            
            # Create HTTP response
            response = HttpResponse(
                excel_file,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{start_date or "all"}_{end_date or "all"}.xlsx"'
            
            return response
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class ExportPDFView(APIView):
    """Export reports to PDF."""
    
    def get(self, request):
        report_type = request.GET.get('type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if not report_type:
            return Response({'error': 'Report type is required'}, status=400)
        
        # Parse dates
        start_date_obj = None
        end_date_obj = None
        
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                pass
                
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        try:
            # Generate PDF file
            pdf_file = export_to_pdf(report_type, start_date_obj, end_date_obj)
            
            # Create HTTP response
            response = HttpResponse(pdf_file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{start_date or "all"}_{end_date or "all"}.pdf"'
            
            return response
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)