import os
import json
from dotenv import load_dotenv
load_dotenv('.env')

from supabase import create_client
sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY'))

# get latest job log
r = sb.table('job_logs').select('id').order('created_at', desc=True).limit(5).execute()
for log in r.data:
    ev = sb.table('job_events').select('*').eq('job_log_id', log['id']).order('created_at', desc=True).limit(10).execute()
    for e in ev.data:
        if 'Error processing sequence' in e['message']:
            print(e['message'])
            import sys
            sys.exit(0)
