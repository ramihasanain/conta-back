from django.db import models
from django.contrib.auth.models import User

class Folder(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Document(models.Model):
    title = models.CharField(max_length=255)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    content = models.TextField(blank=True, null=True)
    file_path = models.FileField(upload_to='documents/', null=True, blank=True)
    status = models.CharField(max_length=50, default='draft') # empty, draft, in_review, completed
    is_starred = models.BooleanField(default=False)
    is_trashed = models.BooleanField(default=False)
    ai_metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class DocumentEditHistory(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='edit_histories')
    type = models.CharField(max_length=50) # manual, ai
    description = models.CharField(max_length=255)
    user = models.CharField(max_length=100, null=True, blank=True)
    oldText = models.TextField(null=True, blank=True)
    newText = models.TextField(null=True, blank=True)
    time = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.document.title}"

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(default=1)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=100, default='System')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Version {self.version_number} - {self.document.title}"

import uuid

class Signature(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signatures')
    signer_name = models.CharField(max_length=255)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    signature_data = models.TextField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default='pending') # pending, completed

    def __str__(self):
        return f"{self.signer_name} - {self.document.title}"

class Workflow(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='workflows')
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default='active')
    current_step_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SavedSignature(models.Model):
    title = models.CharField(max_length=100)
    signature_data = models.TextField() # Data URL of the signature image
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=100, default='Employee')
    permissions = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class WorkflowStep(models.Model):
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=255)
    role_required = models.CharField(max_length=100, blank=True, null=True) # E.g., 'Legal', 'Finance', or specific employee username
    status = models.CharField(max_length=50, default='pending') # pending, approved, rejected
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    assigned_user = models.ForeignKey(User, related_name='assigned_workflow_steps', on_delete=models.SET_NULL, null=True, blank=True)
    comments = models.TextField(blank=True, null=True)
    comment_visibility = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.workflow.name} - {self.title}"

class DocumentPermission(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_permissions')
    permission_level = models.CharField(max_length=50, choices=[('view', 'View'), ('edit', 'Edit'), ('comment', 'Comment')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('document', 'user')

    def __str__(self):
        return f"{self.user.username} - {self.permission_level} on {self.document.title}"

class WorkflowTemplate(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class WorkflowTemplateStep(models.Model):
    template = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name='steps')
    title = models.CharField(max_length=255)
    role_required = models.CharField(max_length=100, blank=True, null=True)
    assigned_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.template.name} - {self.title}"

class InvoiceTemplate(models.Model):
    name = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    default_terms = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
