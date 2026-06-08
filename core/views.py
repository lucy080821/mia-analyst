from django.shortcuts import render


def get_template_name(request, base_name, is_super=False):
    lang = getattr(request, 'LANGUAGE_CODE', 'vi')
    
    name = base_name
    if is_super:
        # management/users.html -> management/super_users.html
        parts = base_name.split('/')
        if len(parts) > 1:
            parts[-1] = 'super_' + parts[-1]
            name = '/'.join(parts)
        else:
            name = 'super_' + base_name

    if '/en/' in request.path or lang == 'en':
        return name.replace('.html', '_en.html')
    return name

def home(request):
    return render(request, get_template_name(request, 'landing.html'))

def features(request):
    return render(request, get_template_name(request, 'pages/features.html'))

def roadmap(request):
    return render(request, get_template_name(request, 'pages/roadmap.html'))

def docs(request):
    return render(request, get_template_name(request, 'pages/docs.html'))

def privacy(request):
    return render(request, get_template_name(request, 'pages/privacy.html'))

def terms(request):
    return render(request, get_template_name(request, 'pages/terms.html'))

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from management.models import SalesLead

@csrf_exempt
def sales_chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        message = body.get("message", "").strip()
        session_id = body.get("session_id", "")
        
        if not message or not session_id:
            return JsonResponse({"error": "Missing message or session_id"}, status=400)
            
        # Get or create SalesLead
        lead, created = SalesLead.objects.get_or_create(
            session_id=session_id,
            defaults={'chat_history': [], 'collected_info': {}}
        )
        
        # Attach user if authenticated
        if request.user.is_authenticated and not lead.user:
            lead.user = request.user
            lead.save()

        # Build prompt
        system_prompt = """You are Mia, an enthusiastic, highly professional, and deeply caring Sales Representative & Consultant for Mia SCM - a premium Supply Chain Co-pilot SaaS platform.
        Your goal is to proactively consult users, listen to their needs, offer passionate and personalized advice, and gently collect information to qualify them as leads.
        Always show deep empathy for their business challenges and excitement about how Mia SCM can solve them.
        
        Information you want to collect if possible:
        - Company size or industry.
        - Their main data pain points (needs).
        - Budget or current tools they use.
        - Contact info (Phone, Email) if they seem ready for Enterprise or need direct consultation.
        
        Product Info (WE ONLY HAVE 3 TIERS):
        - Basic (Free): 20 AI queries/mo, analyze 1 Excel/CSV file, text reports, basic Dashboard.
        - Advanced (499,000 VND/mo): Unlimited AI queries (GPT-4o), ML forecasting, Google Sheets sync, Looker Studio connection, automated Telegram/Email reports, PDF/Excel exports.
        - Enterprise (Custom pricing / Contact Us): Everything in Advanced + Direct Database Connections (MySQL, PostgreSQL, SQL Server), Smart Data Warehouse, Automated ETL, 1:1 Consulting. NEVER reveal exact pricing for Enterprise, always ask them to contact sales or leave their info.
        
        CRITICAL RULES:
        1. LANGUAGE: You MUST analyze the language of the user's LATEST message. IF THE USER SPEAKS ENGLISH, YOUR ENTIRE JSON RESPONSE MUST BE IN ENGLISH. IF THE USER SPEAKS VIETNAMESE, YOUR RESPONSE MUST BE IN VIETNAMESE. THIS IS A HARD CONSTRAINT.
        2. FORMATTING: NEVER use Markdown. Format your `reply` using beautiful HTML tags (like <p>, <ul>, <li>, <strong>, <br>) with Tailwind CSS classes to make it look professional.
        3. CTA: If the user asks for pricing, quotations, or wants to buy, provide a CTA in the `cta_html` field. Use EXACTLY this link: `/auth/upgrade/`. Example in English: `<a href="/auth/upgrade/" class="btn-cta">View Pricing</a>`. Example in Vietnamese: `<a href="/auth/upgrade/" class="btn-cta">Xem bảng giá</a>`.
        4. SUGGESTIONS (Quick Replies for the User): Generate exactly TWO (2) short phrases/questions that the USER can click to reply to YOU. These are options FOR THE USER to say to you. E.g., if you ask their company size, suggestions could be: ["Small (1-50)", "Large (50+)"]. If you just explained features, suggestions could be: ["How much does it cost?", "Can I try it?"].
        5. UPSELLING: Whenever there is a natural opportunity, you MUST gently upsell the Advanced or Enterprise tier. Emphasize how their business can save time and make more money by utilizing Direct DB Connections, Automated Reports, or Machine Learning forecasting. Make the value irresistible.
        
        Output JSON exactly in this format:
        {
            "reply": "Your beautiful HTML response",
            "cta_html": "HTML for a CTA button or empty string if not needed",
            "suggested_questions": ["Question 1", "Question 2"],
            "extracted_info": {
                "company_size": "...",
                "needs": "...",
                "phone": "...",
                "email": "..."
            }
        }
        Do not use Markdown wrapping for the JSON output.
        """

        # Append new message to history for context
        history = lead.chat_history
        history.append({"role": "user", "content": message})
        
        # Limit history to last 10 messages to avoid token bloat
        chat_context = json.dumps(history[-10:], ensure_ascii=False)

        from analytics.ai_utils import get_generative_model
        ai_model = get_generative_model()
        
        response = ai_model.generate_content(
            [
                system_prompt, 
                f"CHAT HISTORY:\n{chat_context}", 
                f"USER'S LATEST MESSAGE: {message}",
                "CRITICAL INSTRUCTION: You MUST detect the language of the USER'S LATEST MESSAGE. If the user writes in Vietnamese, you MUST generate your entire JSON response in Vietnamese. If English, use English. NEVER reply in English if the user asked in Vietnamese!"
            ],
            generation_config={"response_mime_type": "application/json"}
        )
        
        result = json.loads(response.text)
        
        # Update chat history with AI reply
        history.append({"role": "assistant", "content": result.get("reply", "")})
        lead.chat_history = history
        
        # Merge extracted info
        extracted = result.get("extracted_info", {})
        if isinstance(extracted, dict):
            for k, v in extracted.items():
                if v and str(v).lower() not in ["null", "none", "", "unknown"]:
                    lead.collected_info[k] = v
                    
        lead.save()
        
        return JsonResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
