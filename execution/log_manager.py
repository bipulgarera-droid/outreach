import os
import json
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class JobLogger:
    def __init__(self, job_name):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        self.supabase = create_client(url, key)
        self.job_name = job_name
        self.job_id = None
        
        # Initialize the job log
        try:
            res = self.supabase.table('job_logs').insert({
                'job_name': self.job_name,
                'status': 'running'
            }).execute()
            if res.data:
                self.job_id = res.data[0]['id']
                self.info(f"Started job: {job_name}")
        except Exception as e:
            print(f"Failed to initialize job logger: {e}")

    def log(self, message, level='info'):
        if not self.job_id:
            print(f"[{level.upper()}] {message}")
            return
            
        try:
            # Print to console as well for Railway logs
            print(f"[{self.job_name}] {message}")
            
            # Insert into database
            self.supabase.table('job_events').insert({
                'job_log_id': self.job_id,
                'message': str(message),
                'level': level
            }).execute()
        except Exception as e:
            print(f"Failed to log event: {e}")

    def info(self, message):
        self.log(message, 'info')

    def warning(self, message):
        self.log(message, 'warning')

    def error(self, message):
        self.log(message, 'error')

    def success(self, message):
        self.log(message, 'success')

    def complete(self, status='completed'):
        if not self.job_id:
            return
            
        try:
            self.info(f"Job finished with status: {status}")
            self.supabase.table('job_logs').update({
                'status': status,
                'completed_at': datetime.utcnow().isoformat()
            }).eq('id', self.job_id).execute()
        except Exception as e:
            print(f"Failed to complete job log: {e}")
