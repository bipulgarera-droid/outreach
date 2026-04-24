import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("/Users/bipul/Downloads/ALL WORKSPACES/festivals outreach/.env")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

emails = ["kireet.khurana@climbmedia.com", "anu.j@creativelandasia.com"]

for email in emails:
    c_res = supabase.table("contacts").select("id, status, error_message").eq("email", email).execute()
    if not c_res.data:
        print(f"Contact {email} not found")
        continue
    c = c_res.data[0]
    print(f"\n--- Contact: {email} (Status: {c.get('status')}) ---")
    
    s_res = supabase.table("email_sequences").select("id, step_number, status, scheduled_at, sent_at").eq("contact_id", c["id"]).order("step_number").execute()
    for s in s_res.data:
        print(f"  Step {s.get('step_number')}: status={s.get('status')}, scheduled_at={s.get('scheduled_at')}, sent_at={s.get('sent_at')}")
