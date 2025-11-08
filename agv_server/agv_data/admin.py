from django.contrib import admin
from .models import Agv, ResourceAgent, Booking


@admin.register(ResourceAgent)
class ResourceAgentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'resource_type']
    list_filter = ['resource_type']
    search_fields = ['name']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'resource', 'agv_id', 'start_time', 'end_time']
    list_filter = ['resource', 'start_time']
    search_fields = ['agv_id', 'resource__name']
    date_hierarchy = 'start_time'


# Register your models here.
admin.site.register(Agv)
