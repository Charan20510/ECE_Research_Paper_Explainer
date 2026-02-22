from django.contrib import admin
from .models import UploadedPaper


@admin.register(UploadedPaper)
class UploadedPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
