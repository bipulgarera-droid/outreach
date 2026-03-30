import os
import sys
import json
import google.generativeai as genai
from supabase import create_client

def generate_draft_reply(project_id, incoming_text, recipient_name=None):
    """
    Generates a draft reply based on project knowledge base and incoming message.
    """
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    genai_api_key = os.getenv('GEMINI_API_KEY')

    if not all([supabase_url, supabase_key, genai_api_key]):
        return "Error: Missing configuration (Supabase/Gemini)"

    supabase = create_client(supabase_url, supabase_key)
    genai.configure(api_key=genai_api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 1. Fetch Knowledge Base
    kb_res = supabase.table('project_knowledge_base').select('title, content').eq('project_id', project_id).execute()
    kb_items = kb_res.data or []
    
    # 2. Fetch Project Context
    proj_res = supabase.table('projects').select('name, description, custom_instructions').eq('id', project_id).single().execute()
    proj = proj_res.data or {}

    kb_context = "\n".join([f"Q: {item['title']}\nA: {item['content']}" for item in kb_items])
    
    prompt = f"""
You are an expert sales assistant managing email outreach for "{proj.get('name', 'this project')}".
Your goal is to draft a polite, professional, and high-conversion reply to an interested prospect.

PROJECT CONTEXT:
{proj.get('description', '')}

SPECIFIC INSTRUCTIONS:
{proj.get('custom_instructions', 'Be concise and focus on booking a call.')}

KNOWLEDGE BASE / FAQ:
{kb_context if kb_context else "No specific FAQ provided. Use general professional knowledge."}

INCOMING MESSAGE FROM {recipient_name or 'the prospect'}:
---
{incoming_text}
---

TASK:
- Draft a response that directly addresses their points.
- If they asked a question, use the Knowledge Base provided.
- If they are interested, suggest a meeting (be specific, e.g., "Would you have 15 mins later this week?").
- Keep it under 100 words. 
- Do NOT include placeholders like [My Name]. Just write the body text.
- Use a friendly but professional tone.

OUTPUT ONLY THE EMAIL BODY.
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating draft: {str(e)}"

if __name__ == "__main__":
    # Test script
    if len(sys.argv) > 2:
        pid = sys.argv[1]
        msg = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else "Prospect"
        print(generate_draft_reply(pid, msg, name))
    else:
        print("Usage: python generate_reply.py <project_id> <message_text> [name]")
