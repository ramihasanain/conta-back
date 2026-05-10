import os
import json
import requests
from pypdf import PdfReader
from docx import Document as DocxDocument
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Document

API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB9qktaFJDGx6Qz_ytTKkmaUy1HWBIFT8o")

def get_gemini_prompt(company_name):
    return f"""
You are Fossa Intelligence, an elite legal AI.
I am providing you with the extracted text of a document. The text is separated into individual physical pages.
You must analyze the document and return a valid JSON object ONLY, with NO markdown block formatting around it (do not use ```json or ```).

CRITICAL INSTRUCTIONS:
1. The input is separated by [START OF PAGE X] and [END OF PAGE X] markers.
2. You MUST preserve this pagination. Wrap the HTML output for EACH physical page independently inside its own `<div class="a4-page-sheet" dir="auto">...</div>` block.
3. If the text is Arabic, add `style="text-align: right; direction: rtl;"` to those divs. Do NOT merge the pages into one block.
4. Preserve the structure: use <h3> for sections, <p> for clauses, and <ul>/<li> for bullet points.
5. PROOFREADING: While generating the cleanHtml, quietly fix any minor spelling/grammatical errors. Whenever you find an error, you MUST wrap the original erroneous text in a span like this:
   `<span class="fossa-correction" data-suggestion="[YOUR_CORRECTED_TEXT]">[ORIGINAL_TEXT_WITH_ERROR]</span>`
6. PHASES & INVOICES EXTRACTION: Pay extremely close attention to the payment schedule, milestones, or project phases. Extract EACH distinct phase into the 'phases' array. You MUST calculate and provide 'startDate' and 'endDate' (YYYY-MM-DD) for EACH phase based on the contract start date and the phase's relative timeline. ALSO, extract EACH distinct payment/invoice milestone into the 'invoices' array. Provide a strict 'dueDate' in YYYY-MM-DD. Set all extracted invoices to "status": "pending".
7. COMPANY IDENTIFICATION: The user uploading this document belongs to the company: "{company_name}". You MUST analyze the parties in the document. If "{company_name}" (or any reasonable variation, abbreviation, or legal entity format of it) is explicitly mentioned as a party (Primary or Secondary, or buyer/seller/client/vendor), set 'isMyCompanyContract' to true. Otherwise, strictly set it to false.
8. DOCUMENT TYPE: Analyze the text and strictly categorize it as one of: 'Contract', 'Proposal', 'NDA', 'Invoice', or 'Other'.
9. DEEP EXTRACTION: Carefully extract Operational, Legal, and Risk elements such as latePenalties, taxesIncluded (true if prices are inclusive of taxes), keyDeliverables, intellectualProperty ownership, and keyPointOfContact.

The JSON MUST exactly match this schema:
{{
  "documentType": "Strictly one of: 'Contract', 'Proposal', 'NDA', 'Invoice', or 'Other'",
  "isMyCompanyContract": true,
  "startDate": "Extract start date in strictly YYYY-MM-DD format, or null if not found",
  "endDate": "Extract end date in strictly YYYY-MM-DD format, or null if not found",
  "primaryParty": "...",
  "secondaryParty": "...",
  "summary": "...",
  "contractValueNumber": 0,
  "contractCurrency": "USD, JOD, EUR, etc...",
  "numberOfPhases": 0,
  "phases": [
    {{
      "phaseName": "Name or number of the phase",
      "amountNumber": 0,
      "amountCurrency": "USD, JOD, EUR, etc...",
      "tiedToDelivery": true,
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD"
    }}
  ],
  "invoices": [
    {{
      "description": "e.g., Advance Payment, Milestone 1, Final Delivery...",
      "amountNumber": 0,
      "amountCurrency": "USD",
      "dueDate": "YYYY-MM-DD",
      "status": "pending"
    }}
  ],
  "paymentTerms": "e.g., Net 30, Upon Delivery, Retainer...",
  "autoRenewal": true,
  "terminationNoticePeriod": "e.g., 30 days written notice",
  "confidentialityIncluded": true,
  "executionTimeline": "When it started or when it is scheduled to start...",
  "governingLaw": "The jurisdiction or State/Country law governing the contract",
  "liabilityCap": "Maximum damages or liability amount",
  "latePenalties": "Extract any late payment or late delivery penalties (e.g., 1% per week) or 'None' if not specified",
  "taxesIncluded": true,
  "keyDeliverables": "Bullet points of the main deliverables or services provided",
  "intellectualProperty": "Who owns the IP (e.g., Client, Vendor, Shared) and brief details",
  "keyPointOfContact": "Name, email, or role of the primary contact person mentioned",
  "cleanHtml": "<div class='a4-page-sheet' dir='auto'>Page 1 content here... <span class='fossa-correction' data-suggestion='the'>teh</span> error...</div>"
}}

Text to Analyze:
"""

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_contract(request):
    company_name = request.POST.get('company_name', 'Unknown')
    
    if 'file' not in request.FILES:
        return Response({'detail': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
    
    file = request.FILES['file']
    force_upload = request.POST.get('force_upload', 'false').lower() == 'true'
    
    if not force_upload and Document.objects.filter(title=file.name, is_trashed=False).exists():
        return Response({
            'detail': 'A document with this name already exists. Do you want to proceed?',
            'is_duplicate': True
        }, status=status.HTTP_409_CONFLICT)
        
    file_ext = file.name.lower().split('.')[-1]
    if file_ext not in ['pdf', 'docx', 'doc']:
        return Response({'detail': 'Only PDF and Word files are supported.'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        text = ""
        if file_ext == 'pdf':
            reader = PdfReader(file)
            for idx, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    text += f"\n\n[START OF PAGE {idx+1}]\n{extracted}\n[END OF PAGE {idx+1}]\n\n"
        elif file_ext in ['docx', 'doc']:
            doc_reader = DocxDocument(file)
            # For Word docs we might not have 'pages' easily, so we just append text in chunks
            # We'll treat every paragraph as part of page 1 to satisfy the prompt structure
            paragraphs = []
            for p in doc_reader.paragraphs:
                if p.text.strip():
                    paragraphs.append(p.text.strip())
            
            combined_text = "\n".join(paragraphs)
            text = f"\n\n[START OF PAGE 1]\n{combined_text}\n[END OF PAGE 1]\n\n"
                
        if not text.strip():
            return Response({
                'detail': 'Could not extract text from this file. It might be a scanned image or empty.',
                'isImage': True 
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'detail': f'Error reading file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
    # Send to Gemini via direct REST API
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": f"{get_gemini_prompt(company_name)}\n\n{text}"}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        r = requests.post(url, json=payload, headers=headers, timeout=90)
        
        if r.status_code != 200:
            return Response({'detail': f'AI Processing failed: {r.text}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        json_resp = r.json()
        response_text = json_resp['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Robust markdown stripping
        import re
        response_text = re.sub(r'^```(json|html)?\s*', '', response_text, flags=re.IGNORECASE)
        response_text = re.sub(r'\s*```$', '', response_text)
        response_text = response_text.strip()
        
        try:
            ai_data = json.loads(response_text)
        except Exception as json_e:
            with open("gemini_error.txt", "w", encoding="utf-8") as f:
                f.write(response_text)
            raise Exception(f"JSON Decode Error: {str(json_e)}")
            
    except Exception as e:
        import traceback
        with open("gemini_error_trace.txt", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
            f.write(f"\nResponse (if network error): {getattr(r, 'text', 'No network response')}")
        return Response({'detail': f'AI Parsing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Save to Database as a Document
    doc = Document.objects.create(
        title=file.name,
        content=ai_data.get('cleanHtml', text),
        status='Needs Review',
        ai_metadata=ai_data
    )
    
    return Response({
        'document_id': doc.id,
        'title': doc.title,
        'status': doc.status,
        'created_at': doc.created_at,
        'ai_metadata': ai_data
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def fossa_generate_contract(request):
    prompt = request.data.get('prompt')
    if not prompt:
         return Response({'error': 'Prompt is required.'}, status=400)
    
    instruction = f"""
    You are Fossa, a world-class legal AI architect. The user wants you to generate a completely new contract from scratch based on the following request:
    "{prompt}"
    
    CRITICAL INSTRUCTIONS:
    1. Output strictly in HTML. Do NOT wrap it in ```html markdown markers.
    2. Format it using professional enterprise styling. Use <h1 style="text-align:center; color:#1e293b;">, <h3>, <p>, and <ul>.
    3. Ensure there are signature blocks at the very end.
    4. Provide dummy but realistic names if none are provided.
    5. Be comprehensive but concise.
    6. If the user specifies a start and end date, ensure all payment schedules, milestones, and invoice dates generated in the contract strictly adhere to and are calculated based on that timeline.
    """
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": instruction}]}]
        }
        r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=90)
        if r.status_code != 200:
            return Response({'error': f'AI Engine error: {r.text}'}, status=500)
            
        text = r.json()['candidates'][0]['content']['parts'][0]['text']
        if text.startswith('```html'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
            
        doc = Document.objects.create(
            title="AI Generated Contract",
            content=text.strip(),
            status='draft'
        )
        return Response({'id': doc.id, 'title': doc.title, 'status': doc.status}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def fossa_modify_text(request):
    text = request.data.get('text')
    instruction = request.data.get('instruction')
    
    prompt = f"""
    You are Fossa, a brilliant legal AI.
    The user has highlighted the following text in their contract:
    "{text}"
    
    The user is asking you to modify it with this instruction:
    "{instruction}"
    
    Return ONLY the exact replacement HTML snippet. Do not use any markdown formatting or wrappers like ```html. Just return the raw text/HTML to be inserted.
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
        payload = { "contents": [{"parts": [{"text": prompt}]}] }
        r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=90)
        result = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        
        if result.startswith('```html'):
            result = result[7:]
        if result.startswith('```'):
            result = result[3:]
        if result.endswith('```'):
            result = result[:-3]
            
        return Response({'text': result.strip()})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def fossa_chat(request):
    message = request.data.get('message')
    context = request.data.get('context', '')
    history = request.data.get('history', [])
    
    formatted_history = ""
    for msg in history[-4:]: # Keep last 4 for brevity
        formatted_history += f"\n{msg['role']}: {msg['content']}"
        
    prompt = f"""
    You are Fossa, an elite and professional AI legal assistant for an enterprise system.
    Here is the context of the user's current document:
    ---
    {context[:3000]} # Limit to 3000 chars of context
    ---
    
    Recent Chat History:
    {formatted_history}
    
    User: {message}
    Fossa:
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
        payload = { "contents": [{"parts": [{"text": prompt}]}] }
        r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=90)
        result = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        return Response({'message': result})
    except Exception as e:
        return Response({'error': str(e)}, status=500)



