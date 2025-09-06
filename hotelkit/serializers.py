from rest_framework import serializers
from .models import RepairRequest


class RepairRequestSerializer(serializers.ModelSerializer):
    """Serializer for RepairRequest model."""
    
    is_closed = serializers.ReadOnlyField()
    is_open = serializers.ReadOnlyField()
    sla_4h_compliant = serializers.ReadOnlyField()
    sla_24h_compliant = serializers.ReadOnlyField()
    sla_48h_compliant = serializers.ReadOnlyField()
    
    class Meta:
        model = RepairRequest
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class RepairRequestKPISerializer(serializers.Serializer):
    """Serializer for KPI data."""
    avg_response_time = serializers.DurationField()
    avg_completion_time = serializers.DurationField()
    avg_execution_time = serializers.DurationField()
    open_requests = serializers.IntegerField()


class RepairRequestTrendSerializer(serializers.Serializer):
    """Serializer for trend data."""
    date = serializers.DateField()
    created_count = serializers.IntegerField()
    closed_count = serializers.IntegerField()


class RepairRequestTypeSerializer(serializers.Serializer):
    """Serializer for type distribution data."""
    type = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class RepairRequestHeatmapSerializer(serializers.Serializer):
    """Serializer for heatmap data."""
    location = serializers.CharField()
    count = serializers.IntegerField()
    floor = serializers.CharField(allow_null=True)


class RepairRequestTopRoomsSerializer(serializers.Serializer):
    """Serializer for top rooms data."""
    location = serializers.CharField()
    count = serializers.IntegerField()
    avg_completion_time = serializers.DurationField(allow_null=True)


class RepairRequestTechnicianSerializer(serializers.Serializer):
    """Serializer for technician performance data."""
    technician = serializers.CharField()
    count = serializers.IntegerField()
    avg_response_time = serializers.DurationField(allow_null=True)
    avg_completion_time = serializers.DurationField(allow_null=True)


class RepairRequestSLASerializer(serializers.Serializer):
    """Serializer for SLA compliance data."""
    sla_period = serializers.CharField()
    compliant_count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    compliance_rate = serializers.FloatField()
