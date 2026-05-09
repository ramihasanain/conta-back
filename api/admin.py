from django.contrib import admin
from .models import Folder, Document, Signature, Workflow

# Customizing the display in Django Admin
@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'folder', 'status', 'created_at')
    list_filter = ('status', 'folder')
    search_fields = ('title',)

@admin.register(Signature)
class SignatureAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'signer_name', 'status', 'signed_at')
    list_filter = ('status',)
    search_fields = ('signer_name', 'document__title')

@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'document', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'document__title')
