from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Folder, Document, Signature, Workflow
from .serializers import FolderSerializer, DocumentSerializer, SignatureSerializer, WorkflowSerializer
from django.utils import timezone
from datetime import timedelta
import uuid

# --- Folders ---
@api_view(['GET', 'POST'])
def folder_list(request):
    if request.method == 'GET':
        folders = Folder.objects.all().order_by('-created_at')
        serializer = FolderSerializer(folders, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = FolderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def folder_detail(request, pk):
    try:
        folder = Folder.objects.get(pk=pk)
    except Folder.DoesNotExist:
        return Response({'error': 'Folder not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = FolderSerializer(folder)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = FolderSerializer(folder, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        folder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Documents ---
@api_view(['GET', 'POST', 'DELETE'])
def document_list(request):
    if request.method == 'GET':
        view_type = request.GET.get('view', 'recent')
        if view_type == 'starred':
            documents = Document.objects.filter(is_trashed=False, is_starred=True).order_by('-updated_at')
        elif view_type == 'trash':
            documents = Document.objects.filter(is_trashed=True).order_by('-updated_at')
        else:
            # Default recent view
            documents = Document.objects.filter(is_trashed=False).order_by('-updated_at')
            
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def document_detail(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DocumentSerializer(document)
        return Response(serializer.data)
    elif request.method in ['PUT', 'PATCH']:
        partial = request.method == 'PATCH'
        serializer = DocumentSerializer(document, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        hard = request.GET.get('hard', 'false').lower() == 'true'
        if hard:
            document.delete()
        else:
            document.is_trashed = True
            document.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['DELETE'])
def empty_trash(request):
    Document.objects.filter(is_trashed=True).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

# --- Signatures ---
@api_view(['GET', 'POST'])
def signature_list(request):
    if request.method == 'GET':
        signatures = Signature.objects.all()
        serializer = SignatureSerializer(signatures, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = SignatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def generate_signature_link(request):
    document_id = request.data.get('document_id')
    signer_name = request.data.get('signer_name', 'External Guest')
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)
        
    if Signature.objects.filter(document=document, status='completed').exists():
        return Response({'error': 'Document has already been successfully signed and is locked.'}, status=400)
        
    expires_at = timezone.now() + timedelta(hours=24)
    signature = Signature.objects.create(
        document=document,
        signer_name=signer_name,
        expires_at=expires_at,
        status='pending'
    )
    return Response({
        'token': str(signature.token),
        'expires_at': signature.expires_at
    }, status=201)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def guest_signature(request, token):
    try:
        signature = Signature.objects.get(token=token)
    except Signature.DoesNotExist:
        return Response({'error': 'Invalid or expired signature link'}, status=404)
        
    if signature.expires_at and timezone.now() > signature.expires_at:
        return Response({'error': 'Signature link has expired'}, status=400)
        
    if request.method == 'GET':
        return Response({
            'document_title': signature.document.title,
            'document_content': signature.document.content,
            'signer_name': signature.signer_name,
            'status': signature.status
        })
        
    elif request.method == 'POST':
        if signature.status == 'completed':
            return Response({'error': 'Document is already signed'}, status=400)
            
        signature_data = request.data.get('signature_data')
        if not signature_data:
            return Response({'error': 'Signature data is required'}, status=400)
            
        signature.signature_data = signature_data
        signature.status = 'completed'
        signature.signed_at = timezone.now()
        signature.save()

        # Inject into document visually
        doc = signature.document
        
        has_id = 'id="sig-target"' in doc.content or 'id=sig-target' in doc.content
        has_text = '[ CLIENT SIGNATURE GOES HERE ]' in doc.content

        if doc.content and (has_id or has_text):
            import re
            date_str = timezone.now().strftime("%Y-%m-%d %H:%M UTC")
            
            if signature_data.startswith('data:image/'):
                visual_sig = f'<img src="{signature_data}" style="max-height: 80px; display: block; margin: 0 auto; margin-bottom: 8px;" />'
            else:
                visual_sig = f'<div style="font-family: \'Caveat\', cursive; font-size: 28px; font-weight: bold; margin-bottom: 8px;">{signature_data}</div>'

            new_block = f'<div id="sig-target" style="border: 2px solid #16a34a; padding: 20px; text-align: center; margin: 20px 0; background: #f0fdf4; color: #16a34a; border-radius: 8px; width: 300px; display: inline-block;">{visual_sig}<div style="font-size: 10px; color: #475569; font-family: sans-serif; text-transform: uppercase;">Digitally Signed & Verified By Client<br/>{date_str}</div></div>'
            
            # Try structured div replacement first
            old_len = len(doc.content)
            doc.content = re.sub(r'<div[^>]*id=[\'"]?sig-target[\'"]?[^>]*>.*?</div>', new_block, doc.content, flags=re.DOTALL|re.IGNORECASE)
            
            # If the browser's contentEditable stripped the id during an inline-merge, fallback to text replacement
            if len(doc.content) == old_len and has_text:
                # Optionally strip the surrounding span if it's there
                doc.content = re.sub(r'<span[^>]*>\s*\[\s*CLIENT SIGNATURE GOES HERE\s*\]\s*</span>', new_block, doc.content, flags=re.IGNORECASE)
                # Raw text fallback just in case
                doc.content = doc.content.replace('[ CLIENT SIGNATURE GOES HERE ]', new_block)
            
        doc.status = 'completed'
        if not doc.ai_metadata:
            doc.ai_metadata = {}
        doc.ai_metadata['contractType'] = 'Signed Contract'
        doc.save()

        return Response({'success': True, 'message': 'Document signed successfully'})


# --- Workflows ---
@api_view(['GET', 'POST'])
def workflow_list(request):
    if request.method == 'GET':
        document_id = request.GET.get('document_id')
        if document_id:
            workflows = Workflow.objects.filter(document_id=document_id).order_by('-created_at')
        else:
            workflows = Workflow.objects.all().order_by('-created_at')
        serializer = WorkflowSerializer(workflows, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = WorkflowSerializer(data=request.data)
        if serializer.is_valid():
            workflow = serializer.save()
            
            # Handle nested steps
            steps_data = request.data.get('steps', [])
            from .models import WorkflowStep
            for index, step_data in enumerate(steps_data):
                WorkflowStep.objects.create(
                    workflow=workflow,
                    title=step_data.get('name', f'Step {index+1}'),
                    role_required=step_data.get('role', ''),
                    order=index
                )
                
            return Response(WorkflowSerializer(workflow).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Saved Signatures ---
from .models import SavedSignature
from .serializers import SavedSignatureSerializer

@api_view(['GET', 'POST'])
def saved_signature_list(request):
    if request.method == 'GET':
        signatures = SavedSignature.objects.all().order_by('-created_at')
        serializer = SavedSignatureSerializer(signatures, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        # If set to default, unset others
        if request.data.get('is_default', False):
            SavedSignature.objects.update(is_default=False)
            
        serializer = SavedSignatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def saved_signature_detail(request, pk):
    try:
        sig = SavedSignature.objects.get(pk=pk)
        sig.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except SavedSignature.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

from .models import DocumentEditHistory
from .serializers import DocumentEditHistorySerializer

@api_view(['GET', 'POST'])
def document_history(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        history = DocumentEditHistory.objects.filter(document=document).order_by('-created_at')
        serializer = DocumentEditHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # Smart Grouping (if it's a PATCH to the latest manual record via POST payload)
        action = request.data.get('_action')
        if action == 'smart_update':
            hist_id = request.data.get('id')
            try:
                hist = DocumentEditHistory.objects.get(pk=hist_id, document=document)
                hist.newText = request.data.get('newText', hist.newText)
                hist.time = request.data.get('time', hist.time)
                hist.save()
                return Response(DocumentEditHistorySerializer(hist).data, status=status.HTTP_200_OK)
            except DocumentEditHistory.DoesNotExist:
                # Fallback to create
                pass

        data = request.data.copy()
        data['document'] = document.id
        serializer = DocumentEditHistorySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import DocumentVersion
from .serializers import DocumentVersionSerializer

@api_view(['GET', 'POST'])
def document_versions(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        versions = DocumentVersion.objects.filter(document=document).order_by('-created_at')
        serializer = DocumentVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        last_version = DocumentVersion.objects.filter(document=document).order_by('-version_number').first()
        next_ver = 1 if not last_version else last_version.version_number + 1
        
        data = request.data.copy()
        data['document'] = document.id
        data['version_number'] = next_ver
        
        serializer = DocumentVersionSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .models import DocumentPermission, WorkflowStep
from .serializers import DocumentPermissionSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from django.contrib.auth.models import User

@api_view(['GET', 'POST', 'DELETE'])
def document_permissions(request, pk):
    try:
        document = Document.objects.get(pk=pk)
    except Document.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        perms = DocumentPermission.objects.filter(document=document)
        serializer = DocumentPermissionSerializer(perms, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        user_id = request.data.get('user_id')
        permission_level = request.data.get('permission_level')
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
            
        perm, created = DocumentPermission.objects.update_or_create(
            document=document,
            user=user,
            defaults={'permission_level': permission_level}
        )
        return Response(DocumentPermissionSerializer(perm).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    elif request.method == 'DELETE':
        user_id = request.data.get('user_id') or request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            perm = DocumentPermission.objects.get(document=document, user_id=user_id)
            perm.delete()
            return Response({'status': 'deleted'}, status=status.HTTP_204_NO_CONTENT)
        except DocumentPermission.DoesNotExist:
            return Response({'error': 'Permission not found'}, status=status.HTTP_404_NOT_FOUND)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_approvals(request):
    user = request.user
    steps = WorkflowStep.objects.filter(assigned_user=user, status__in=['pending', 'returned'])
    documents = []
    for step in steps:
        if step.workflow and step.workflow.document and step.order == step.workflow.current_step_order:
            if step.workflow.document not in documents:
                step.workflow.document.pending_step_status = step.status
                documents.append(step.workflow.document)
                
    serializer = DocumentSerializer(documents, many=True)
    data = serializer.data
    for i, doc in enumerate(data):
        doc['pending_step_status'] = documents[i].pending_step_status
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def workflow_step_action(request, pk):
    try:
        step = WorkflowStep.objects.get(pk=pk)
    except WorkflowStep.DoesNotExist:
        return Response({'error': 'Step not found'}, status=status.HTTP_404_NOT_FOUND)
        
    action = request.data.get('action') # 'approve' or 'reject'
    comment = request.data.get('comment', '')
    comment_visibility = request.data.get('comment_visibility', [])
    
    if step.assigned_user != request.user:
        return Response({'error': 'Not assigned to you'}, status=status.HTTP_403_FORBIDDEN)
        
    workflow = step.workflow
    if step.order != workflow.current_step_order:
        return Response({'error': 'Not your turn in sequence'}, status=status.HTTP_400_BAD_REQUEST)
        
    step.comments = comment
    if isinstance(comment_visibility, list):
        step.comment_visibility = comment_visibility
        
    if action == 'approve':
        step.status = 'approved'
        step.approved_by = request.user
        step.approved_at = timezone.now()
        step.save()
        
        workflow.current_step_order += 1
        workflow.save()
        
        next_step = WorkflowStep.objects.filter(workflow=workflow, order=workflow.current_step_order).first()
        if next_step and next_step.status in ['rejected', 'returned']:
            next_step.status = 'pending'
            next_step.save()
            
        return Response({'success': True, 'status': 'approved'})
        
    elif action == 'reject':
        step.status = 'rejected'
        step.save()
        
        if workflow.current_step_order > 0:
            workflow.current_step_order -= 1
            workflow.save()
            
            prev_step = WorkflowStep.objects.filter(workflow=workflow, order=workflow.current_step_order).first()
            if prev_step:
                prev_step.status = 'returned'
                prev_step.save()
                
        return Response({'success': True, 'status': 'rejected'})
        
    return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def workflow_add_step(request, pk):
    try:
        workflow = Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return Response({'error': 'Workflow not found'}, status=status.HTTP_404_NOT_FOUND)
    
    assigned_user_id = request.data.get('assigned_user_id')
    user = None
    if assigned_user_id:
        try:
            user = User.objects.get(pk=assigned_user_id)
        except User.DoesNotExist:
            pass
            
    step = WorkflowStep.objects.create(
        workflow=workflow,
        title=request.data.get('name', 'Step'),
        role_required=request.data.get('role', ''),
        assigned_user=user,
        order=request.data.get('order', 0)
    )
    from .serializers import WorkflowStepSerializer
    return Response(WorkflowStepSerializer(step).data, status=status.HTTP_201_CREATED)

@api_view(['GET', 'POST'])
def workflow_template_list(request):
    from .models import WorkflowTemplate, WorkflowTemplateStep
    from .serializers import WorkflowTemplateSerializer
    from django.contrib.auth.models import User
    
    if request.method == 'GET':
        templates = WorkflowTemplate.objects.all().order_by('-created_at')
        serializer = WorkflowTemplateSerializer(templates, many=True)
        return Response(serializer.data)
        
    elif request.method == 'POST':
        name = request.data.get('name')
        steps_data = request.data.get('steps', [])
        
        if not name:
            return Response({'error': 'Template name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        template = WorkflowTemplate.objects.create(name=name)
        
        for index, step_data in enumerate(steps_data):
            assigned_user_id = step_data.get('assigned_user_id')
            user = None
            if assigned_user_id:
                try:
                    user = User.objects.get(pk=assigned_user_id)
                except User.DoesNotExist:
                    pass
            
            WorkflowTemplateStep.objects.create(
                template=template,
                title=step_data.get('name', f'Step {index+1}'),
                role_required=step_data.get('role', ''),
                assigned_user=user,
                order=index
            )
            
        return Response(WorkflowTemplateSerializer(template).data, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def apply_workflow_template(request):
    from .models import WorkflowTemplate, Workflow, WorkflowStep
    from .serializers import WorkflowSerializer
    
    document_id = request.data.get('document_id')
    template_id = request.data.get('template_id')
    
    if not document_id or not template_id:
        return Response({'error': 'document_id and template_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        template = WorkflowTemplate.objects.get(pk=template_id)
        document = Document.objects.get(pk=document_id)
    except (WorkflowTemplate.DoesNotExist, Document.DoesNotExist):
        return Response({'error': 'Template or Document not found'}, status=status.HTTP_404_NOT_FOUND)
        
    workflow, created = Workflow.objects.get_or_create(
        document=document,
        defaults={'name': f"Workflow for {document.title}"}
    )
    
    max_order = WorkflowStep.objects.filter(workflow=workflow).count()
    
    for step in template.steps.all():
        WorkflowStep.objects.create(
            workflow=workflow,
            title=step.title,
            role_required=step.role_required,
            assigned_user=step.assigned_user,
            order=max_order + step.order
        )
        
    return Response(WorkflowSerializer(workflow).data, status=status.HTTP_200_OK)

# --- Invoices ---
@api_view(['GET', 'PATCH'])
def global_invoices(request):
    if request.method == 'GET':
        all_invoices = []
        documents = Document.objects.filter(is_trashed=False)
        for doc in documents:
            if doc.ai_metadata and 'invoices' in doc.ai_metadata:
                for inv in doc.ai_metadata['invoices']:
                    inv['document_id'] = doc.id
                    inv['document_title'] = doc.title
                    all_invoices.append(inv)
        return Response(all_invoices)
        
    elif request.method == 'PATCH':
        document_id = request.data.get('document_id')
        invoice_id = request.data.get('invoice_id')
        status_val = request.data.get('status')
        
        try:
            doc = Document.objects.get(pk=document_id)
            if doc.ai_metadata and 'invoices' in doc.ai_metadata:
                invoices = doc.ai_metadata['invoices']
                for inv in invoices:
                    if inv.get('id') == invoice_id:
                        if status_val:
                            inv['status'] = status_val
                        break
                doc.ai_metadata['invoices'] = invoices
                doc.save()
                return Response({'success': True})
        except Document.DoesNotExist:
            return Response({'error': 'Document not found'}, status=404)
        return Response({'error': 'Invoice update failed'}, status=400)

from .models import InvoiceTemplate
from .serializers import InvoiceTemplateSerializer

@api_view(['GET', 'POST'])
def invoice_templates(request):
    if request.method == 'GET':
        templates = InvoiceTemplate.objects.all().order_by('-created_at')
        serializer = InvoiceTemplateSerializer(templates, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = InvoiceTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def invoice_template_detail(request, pk):
    try:
        template = InvoiceTemplate.objects.get(pk=pk)
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except InvoiceTemplate.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
