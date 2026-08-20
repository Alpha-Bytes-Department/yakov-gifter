from django.contrib import admin
from apps.parshas.models import Parsha, ReadingSchedule

@admin.register(Parsha)
class ParshaAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_hebrew', 'sefer', 'chapter_verse']
    list_filter = ['sefer']
    search_fields = ['name', 'name_hebrew']
    ordering = ['id']

@admin.register(ReadingSchedule)
class ReadingScheduleAdmin(admin.ModelAdmin):
    list_display = ['parsha', 'date']
    list_filter = ['date']
    ordering = ['-date']
