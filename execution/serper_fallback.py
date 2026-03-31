import os
import json
import logging
from apify_client import ApifyClient

logger = logging.getLogger(__name__)

def verify_risky_emails_bulk(sequences: list[dict], supabase_client) -> None:
    """
    Extracts all 'risky' emails (including Catch-Alls) from the pending pending sequences
    that haven't been OSINT-verified yet, runs them through Apify Google Search in bulk,
    and updates the contact's enrichment_data with `serper_verified`: True/False.
    """
    to_verify = []
    
    for seq in sequences:
        c = seq.get('contacts', {})
        ed = c.get('enrichment_data') or {}
        if isinstance(ed, str):
            try: ed = json.loads(ed)
            except: ed = {}
            seq['contacts']['enrichment_data'] = ed
            
        v_status = ed.get('verification_status')
        v_reason = str(ed.get('verification_reason', ''))
        
        # Identify Risky emails (now includes domain_catch_all)
        is_strict_risky = v_status == 'risky' or (v_status == 'valid' and 'domain_catch_all' in v_reason)
        
        if is_strict_risky:
            has_been_checked = 'serper_verified' in ed
            if not has_been_checked:
                email = c.get('email', '').strip()
                if email and '@' in email:
                    to_verify.append(seq)
                    
    if not to_verify:
        return

    logger.info(f"OSINT FALLBACK: Found {len(to_verify)} unverified risky leads. Preparing bulk Apify check...")

    apify_key = os.getenv('APIFY_API_KEY')
    if not apify_key:
        logger.error("OSINT FALLBACK: No APIFY_API_KEY found in .env. Skipping deep verification.")
        return

    # Build multi-line query string for the actor
    lines = []
    # Use a dict to map the exact email string we send to Apify back to the sequence objects
    email_to_seqs = {}
    
    for seq in to_verify:
        email = seq['contacts']['email'].strip()
        lines.append(f'"{email}"')
        if email not in email_to_seqs:
            email_to_seqs[email] = []
        email_to_seqs[email].append(seq)
        
    # Deduplicate queries to save cost
    unique_lines = list(set(lines))
    keyword_payload = "\n".join(unique_lines)
    
    logger.info(f"OSINT FALLBACK: Initiating Apify 'scraperlink' actor for {len(unique_lines)} unique queries. This may take 60-120 seconds...")
    
    client = ApifyClient(apify_key)
    run_input = {
        "keyword": keyword_payload,
        "include_merged": True,
        "limit": "10"
    }

    try:
        run = client.actor("scraperlink/google-search-results-serp-scraper").call(run_input=run_input)
    except Exception as e:
        logger.error(f"OSINT FALLBACK: Apify Actor call failed: {e}")
        return

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        logger.error("OSINT FALLBACK: No defaultDatasetId returned from Apify.")
        return

    verified_emails = set()
    
    logger.info("OSINT FALLBACK: Apify run complete. Parsing dataset...")
    try:
        for item in client.dataset(dataset_id).iterate_items():
            # Example item['query'] = '"john@example.com"'
            query_val = str(item.get('query', '')).strip().strip('"')
            results = item.get('results', [])
            
            # If Google found at least 1 organic search result containing this email string:
            if isinstance(results, list) and len(results) > 0:
                verified_emails.add(query_val)
    except Exception as e:
        logger.error(f"OSINT FALLBACK: Error reading Apify dataset: {e}")

    # Update the Database
    newly_verified = 0
    newly_rejected = 0
    
    for email, seq_list in email_to_seqs.items():
        is_verified = email in verified_emails
        if is_verified:
            newly_verified += 1
            logger.info(f"  ✅ [OSINT RECOVERED] Found {email} on Google.")
        else:
            newly_rejected += 1
            logger.info(f"  🚫 [OSINT DROPPED] Could not confidently verify {email} on Google.")
            
        for seq in seq_list:
            c_id = seq['contact_id']
            ed = seq['contacts'].get('enrichment_data') or {}
            
            ed['serper_verified'] = is_verified
            
            supabase_client.table('contacts').update({'enrichment_data': ed}).eq('id', c_id).execute()

    logger.info(f"OSINT FALLBACK COMPLETE: Recovered {newly_verified} | Dropped {newly_rejected}.")
