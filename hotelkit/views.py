from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
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
    get_technician_performance, get_sla_compliance
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


class RepairsDashboardView(TemplateView):
    """Dashboard view for repairs analytics."""
    template_name = 'hotelkit/repairs_dashboard.html'
    
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


def repairs_import_view(request):
    """Simple import view for form-based uploads."""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'No file uploaded')
            return redirect('repairs_dashboard')
        
        file = request.FILES['file']
        
        try:
            # Parse the file
            if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                df = parse_excel_file(file)
            else:
                messages.error(request, 'Only Excel files (.xlsx, .xls) are supported')
                return redirect('repairs_dashboard')
            
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
    
    return redirect('repairs_dashboard')