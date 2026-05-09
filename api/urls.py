from django.urls import path
from . import views
from . import views_ai
from . import views_users

urlpatterns = [
    # Folders
    path('folders/', views.folder_list, name='folder-list'),
    path('folders/<int:pk>/', views.folder_detail, name='folder-detail'),
    
    # Documents
    path('documents/', views.document_list, name='document-list'),
    path('documents/empty_trash/', views.empty_trash, name='empty-trash'),
    path('documents/<int:pk>/', views.document_detail, name='document-detail'),
    path('documents/<int:pk>/permissions/', views.document_permissions, name='document-permissions'),
    path('documents/<int:pk>/history/', views.document_history, name='document-history'),
    path('documents/<int:pk>/versions/', views.document_versions, name='document-versions'),
    path('documents/upload/', views_ai.upload_contract, name='upload_contract'),
    
    # Signatures
    path('signatures/', views.signature_list, name='signature-list'),
    path('signatures/generate_link/', views.generate_signature_link, name='generate_signature_link'),
    path('signatures/guest/<uuid:token>/', views.guest_signature, name='guest_signature'),
    
    # Workflows & Templates
    path('workflow-templates/', views.workflow_template_list, name='workflow-template-list'),
    path('workflows/', views.workflow_list, name='workflow-list'),
    path('workflows/apply-template/', views.apply_workflow_template, name='apply-workflow-template'),
    path('workflows/<int:pk>/steps/', views.workflow_add_step, name='workflow-add-step'),
    path('workflows/pending-approvals/', views.pending_approvals, name='pending-approvals'),
    path('workflows/steps/<int:pk>/action/', views.workflow_step_action, name='workflow-step-action'),
    
    # Saved Signatures
    path('saved-signatures/', views.saved_signature_list, name='saved-signature-list'),
    path('saved-signatures/<int:pk>/', views.saved_signature_detail, name='saved-signature-detail'),

    # Fossa AI Core
    path('ai/generate-contract/', views_ai.fossa_generate_contract, name='fossa_generate'),
    path('ai/modify-text/', views_ai.fossa_modify_text, name='fossa_modify'),
    path('ai/chat/', views_ai.fossa_chat, name='fossa_chat'),
    
    # Users / Employees
    path('auth/me/', views_users.get_me, name='get_me'),
    path('users/', views_users.employee_list_create, name='user_list_create'),
    path('users/<int:pk>/', views_users.employee_detail, name='user_detail'),
    
    # Invoices & Payments
    path('invoices/', views.global_invoices, name='global-invoices'),
    path('invoice-templates/', views.invoice_templates, name='invoice-templates'),
    path('invoice-templates/<int:pk>/', views.invoice_template_detail, name='invoice-template-detail'),
]
