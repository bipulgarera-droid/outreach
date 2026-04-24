import os
import csv
from dotenv import load_dotenv
from supabase import create_client

def process():
    workspace_dir = '/Users/bipul/Downloads/ALL WORKSPACES/festivals outreach'
    
    # Load environment variables
    load_dotenv(os.path.join(workspace_dir, '.env'))
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    if not url or not key:
        print("Error: Supabase credentials not found in .env")
        return
        
    sb = create_client(url, key)
    
    # 1. Get the "Film Work" project ID
    res = sb.table('projects').select('id, name').execute()
    film_work_id = None
    for p in res.data:
        if "film work" in p['name'].lower():
            film_work_id = p['id']
            print(f"Found project: {p['name']} -> {film_work_id}")
            break
            
    if not film_work_id:
        print("Error: Could not find 'Film Work' project.")
        return
        
    # 2. Fetch existing companies in "Film Work" project to avoid duplicates
    print("Fetching existing companies in Film Work project...")
    existing_companies = set()
    offset = 0
    while True:
        c_res = sb.table('contacts').select('company').eq('project_id', film_work_id).range(offset, offset + 999).execute()
        if not c_res.data:
            break
        for c in c_res.data:
            if c.get('company'):
                existing_companies.add(c['company'].strip().lower())
        if len(c_res.data) < 1000:
            break
        offset += 1000
        
    print(f"Loaded {len(existing_companies)} existing companies.")
    
    # 3. Read CSV and prepare new entries
    csv_path = os.path.join(workspace_dir, 'Prod houses  - Copy of Sheet1.csv')
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return
        
    new_entries = []
    seen_in_csv = set()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            company_name = row[0].strip()
            if not company_name: continue
            
            comp_lower = company_name.lower()
            
            # Skip if already in database or if we already added it from this CSV
            if comp_lower not in existing_companies and comp_lower not in seen_in_csv:
                seen_in_csv.add(comp_lower)
                new_entries.append({
                    'project_id': film_work_id,
                    'company': company_name,
                    'name': 'Unknown',  # Ensure constraints aren't violated (if name is required)
                    'status': 'new',
                    'source': 'csv_import'
                })
                
    if not new_entries:
        print("No new companies to insert. All companies in CSV are already in the project.")
        return
        
    print(f"Found {len(new_entries)} new companies to insert.")
    
    # 4. Bulk insert new entries
    for i in range(0, len(new_entries), 500):
        batch = new_entries[i:i+500]
        try:
            sb.table('contacts').insert(batch).execute()
            print(f"Inserted batch of {len(batch)} records.")
        except Exception as e:
            print(f"Error inserting batch: {e}")
            
    print("Done!")

if __name__ == '__main__':
    process()
