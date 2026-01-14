from django.contrib import admin
from .models import Program, ProgramItem


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['title', 'date', 'owner', 'is_ready', 'share_token', 'created_at']
    list_filter = ['date', 'created_at', 'shared_at']
    search_fields = ['title', 'description', 'owner__username']
    readonly_fields = ['share_token', 'shared_at', 'created_at', 'updated_at']
    
    def is_ready(self, obj):
        return obj.is_ready
    is_ready.boolean = True


@admin.register(ProgramItem)
class ProgramItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'program', 'start_time', 'end_time', 'position']
    list_filter = ['program', 'start_time']
    search_fields = ['title', 'description', 'program__title']
    ordering = ['program', 'position']