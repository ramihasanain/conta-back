from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Folder, Document, Signature, Workflow, SavedSignature, DocumentEditHistory, DocumentVersion, UserProfile, WorkflowStep, DocumentPermission, WorkflowTemplate, WorkflowTemplateStep, InvoiceTemplate

class InvoiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = '__all__'

class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = '__all__'

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'

class SignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = '__all__'

class WorkflowStepSerializer(serializers.ModelSerializer):
    assigned_user_details = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowStep
        fields = '__all__'

    def get_assigned_user_details(self, obj):
        if obj.assigned_user:
            return {'id': obj.assigned_user.id, 'username': obj.assigned_user.username, 'email': obj.assigned_user.email}
        return None

class DocumentPermissionSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = DocumentPermission
        fields = '__all__'

    def get_user_details(self, obj):
        if obj.user:
            return {'id': obj.user.id, 'username': obj.user.username, 'email': obj.user.email}
        return None

class WorkflowSerializer(serializers.ModelSerializer):
    steps = WorkflowStepSerializer(many=True, read_only=True)
    class Meta:
        model = Workflow
        fields = '__all__'

class WorkflowTemplateStepSerializer(serializers.ModelSerializer):
    assigned_user_details = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplateStep
        fields = '__all__'

    def get_assigned_user_details(self, obj):
        if obj.assigned_user:
            return {'id': obj.assigned_user.id, 'username': obj.assigned_user.username, 'email': obj.assigned_user.email}
        return None

class WorkflowTemplateSerializer(serializers.ModelSerializer):
    steps = WorkflowTemplateStepSerializer(many=True, read_only=True)
    class Meta:
        model = WorkflowTemplate
        fields = '__all__'

class SavedSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSignature
        fields = '__all__'

class DocumentEditHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentEditHistory
        fields = '__all__'

class DocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentVersion
        fields = '__all__'

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['role', 'permissions']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']
