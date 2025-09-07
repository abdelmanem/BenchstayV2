from django.contrib import admin
from .models import RepairRequest
from .guest_requests.models import GuestRequest


@admin.register(RepairRequest)
class RepairRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id_field', 'location', 'type', 'state', 'priority', 
        'creator', 'creation_date', 'completion_time'
    ]
    list_filter = [
        'state', 'priority', 'type', 'creation_date', 'time_done'
    ]
    search_fields = [
        'id_field', 'location', 'type', 'creator', 'text', 'comments'
    ]
    readonly_fields = [
        'response_time', 'work_start_delay', 'completion_time', 
        'execution_time', 'evaluation_time', 'latest_state_delay',
        'created_at', 'updated_at'
    ]
    ordering = ['-creation_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id_field', 'creator', 'recipients', 'location', 'location_path')
        }),
        ('Request Details', {
            'fields': ('type', 'type_path', 'assets', 'ticket', 'priority', 'state')
        }),
        ('Timestamps', {
            'fields': (
                'creation_date', 'time_accepted', 'time_in_progress', 
                'time_done', 'time_in_evaluation', 'latest_state_change_time'
            )
        }),
        ('Calculated Durations', {
            'fields': (
                'response_time', 'work_start_delay', 'completion_time',
                'execution_time', 'evaluation_time', 'latest_state_delay'
            ),
            'classes': ('collapse',)
        }),
        ('Content', {
            'fields': ('text', 'submitted_result', 'comments', 'link')
        }),
        ('Parking Information', {
            'fields': ('parking_reason', 'parking_information'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(GuestRequest)
class GuestRequestAdmin(admin.ModelAdmin):
    list_display = [
        'request_id', 'creator', 'recipients', 'location', 'type',
        'priority', 'state', 'creation_date', 'time_accepted', 'time_done'
    ]
    list_filter = [
        'state', 'priority', 'type', 'creation_date', 'time_done', 'uploaded_at'
    ]
    search_fields = [
        'request_id', 'creator', 'recipients', 'location', 'type', 'priority', 'state'
    ]
    readonly_fields = [
        'response_time', 'completion_time', 'total_duration', 'uploaded_at'
    ]
    ordering = ['-creation_date']

    fieldsets = (
        ('Basic Information', {
            'fields': ('request_id', 'creator', 'recipients', 'location', 'type')
        }),
        ('Status & Priority', {
            'fields': ('priority', 'state')
        }),
        ('Timestamps', {
            'fields': ('creation_date', 'time_accepted', 'time_done')
        }),
        ('Calculated Durations', {
            'fields': ('response_time', 'completion_time', 'total_duration'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        })
    )