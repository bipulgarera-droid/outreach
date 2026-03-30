import imaplib
import email
import os
import re
import socket
import ssl
from datetime import datetime, timedelta
import logging
from email.header import decode_header
from dotenv import load_dotenv

# Constants
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _load_accounts_from_env() -> list[dict]:
    """Load Gmail accounts from .env using GMAIL_N_EMAIL format."""
    accounts = []
    for i in range(1, 25):
        acct_email = os.getenv(f"GMAIL_{i}_EMAIL")
        acct_password = os.getenv(f"GMAIL_{i}_PASSWORD")
        if not acct_email or not acct_password:
            continue
        accounts.append({"email": acct_email.strip(), "app_password": acct_password.strip()})
    return accounts

def _decode_header_value(raw):
    """Safely decode an email header value."""
    if raw is None:
        return ""
    try:
        decoded_parts = decode_header(raw)
        result = ""
        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(charset or "utf-8", errors="replace")
            else:
                result += part
        return result
    except:
        return str(raw)

def _extract_sender_email(from_header: str) -> str:
    """Extract just the email address from a From: header, handling encoded strings."""
    decoded_from = _decode_header_value(from_header)
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', decoded_from)
    if emails:
        return emails[0].strip().lower()
    if "<" in decoded_from and ">" in decoded_from:
        return decoded_from.split("<")[1].split(">")[0].strip().lower()
    return decoded_from.strip().lower()

def _get_imap_connection(acct_email: str, acct_password: str) -> imaplib.IMAP4_SSL:
    """Helper to establish a fresh IMAP connection with timeout."""
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
    mail.login(acct_email, acct_password)
    try:
        mail.select('"[Gmail]/All Mail"')
    except:
        mail.select("INBOX")
    return mail

def _extract_body(msg) -> str:
    """Recursively extract the plain text body from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode('utf-8', errors='ignore')
                except: pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='ignore')
        except: pass
    return body.strip()

def is_bounce(from_addr: str, subject: str) -> bool:
    """Determine if a message is a NDR."""
    f = (from_addr or "").lower()
    s = (subject or "").lower()
    if any(x in f for x in ['mailer-daemon', 'postmaster', 'no-reply@accounts.google.com']):
        return True
    if any(x in s for x in ['undeliverable', 'delivery status notification', 'failure', 'returned mail']):
        return True
    return False

def analyze_sentiment(text: str):
    """Simple keyword-based sentiment."""
    t = text.lower()
    if any(k in t for k in ['not interested', 'remove', 'unsubscribe', 'stop', 'wrong person']):
        return 'Negative', 0.1
    if any(k in t for k in ['interested', 'let\'s talk', 'call', 'meeting', 'sounds good']):
        return 'Positive', 0.9
    return 'Neutral', 0.5

def check_replies_for_account(acct_email, acct_password, prospect_emails, domain_map, days=10, logger_callback=None):
    """Connect and scan for replies/bounces with Absolute Robustness."""
    replied = []
    bounced = []
    mail = None

    def _log(msg):
        logger.info(msg)
        if logger_callback: logger_callback(msg)

    try:
        _log(f"Checking {acct_email}...")
        mail = _get_imap_connection(acct_email, acct_password)

        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        status, message_ids = mail.search(None, f'(SINCE {since_date})')

        if status != "OK" or not message_ids[0]:
            _log(f"[{acct_email}] No recent emails found.")
            mail.logout()
            return [], []

        ids = message_ids[0].split()
        _log(f"[{acct_email}] Scanning {len(ids)} emails from last {days} days...")

        for msg_id in ids:
            try:
                status, msg_data = mail.fetch(msg_id, "(RFC822 X-GM-THRID X-GM-MSGID)")
                if status != "OK" or not msg_data: continue

                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                from_hdr = _decode_header_value(msg.get("From", ""))
                subject_hdr = _decode_header_value(msg.get("Subject", ""))
                sender = _extract_sender_email(from_hdr)
                body_text = _extract_body(msg)
                body_lower = body_text.lower()
                
                # Metadata
                metadata_raw = msg_data[0][0].decode()
                thread_id = re.search(r"X-GM-THRID (\d+)", metadata_raw)
                thread_id = thread_id.group(1) if thread_id else None
                message_id_gmail = re.search(r"X-GM-MSGID (\d+)", metadata_raw)
                message_id_gmail = message_id_gmail.group(1) if message_id_gmail else None

                is_b = is_bounce(from_hdr, subject_hdr)
                found_prospect = None
                
                # --- ABSOLUTE MATCHING ---
                # 1. Direct Email Match
                if sender in prospect_emails:
                    found_prospect = sender
                
                # 2. Domain/Body Match (Marcelo Protection)
                if not found_prospect:
                    # Check body for ALL prospect emails
                    for p_email in prospect_emails:
                        if p_email in body_lower or p_email in from_hdr.lower():
                            found_prospect = p_email
                            break
                    
                    # Check domain map
                    if not found_prospect and domain_map:
                        for domain, p_email in domain_map.items():
                            if domain in body_lower or domain in from_hdr.lower():
                                found_prospect = p_email
                                break

                if found_prospect:
                    if is_b:
                        bounced.append(found_prospect)
                        _log(f"  ❌ Bounce: {found_prospect}")
                    else:
                        sentiment, score = analyze_sentiment(body_text)
                        replied.append({
                            'email': found_prospect,
                            'subject': subject_hdr,
                            'body': body_text,
                            'sentiment': sentiment,
                            'sentiment_score': score,
                            'thread_id': thread_id,
                            'message_id': message_id_gmail,
                            'recipient_email': acct_email
                        })
                        _log(f"  ✅ Reply: {found_prospect}")
            except Exception as e:
                logger.error(f"Error processing message {msg_id}: {e}")

        mail.logout()
    except Exception as e:
        _log(f"FAILED for {acct_email}: {e}")
        if mail:
            try: mail.logout()
            except: pass

    return replied, bounced

def check_replies():
    """Main synchronizer using Service Role Key to bypass RLS."""
    load_dotenv()
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not url or not key:
        return {"error": "Supabase credentials missing"}
    
    from supabase import create_client
    supabase = create_client(url, key)
    
    # Monitor ALL contacts
    res = supabase.table('contacts').select('id, email, website').not_.is_('email', 'null').execute()
    contact_map = {r['email'].strip().lower(): r['id'] for r in res.data}
    prospect_emails = set(contact_map.keys())
    
    # Build Domain Map for colleague/alternate-email detection
    domain_map = {}
    for r in res.data:
        p_email = r['email'].strip().lower()
        # From Email Domain
        ed = p_email.split('@')[-1]
        if len(ed) > 4 and ed not in ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com']:
            domain_map[ed] = p_email
        # From Website
        if r['website']:
            wd = r['website'].replace('https://','').replace('http://','').replace('www.','').split('/')[0].lower()
            if len(wd) > 3:
                domain_map[wd] = p_email
    
    accounts = _load_accounts_from_env()
    all_replies = []
    all_bounces = set()
    
    for acct in accounts:
        r, b = check_replies_for_account(acct['email'], acct['app_password'], prospect_emails, domain_map)
        all_replies.extend(r)
        all_bounces.update(b)
    
    # Save Bounces
    for b_email in all_bounces:
        cid = contact_map.get(b_email.lower())
        if cid:
            supabase.table('contacts').update({'status': 'bounced'}).eq('id', cid).execute()

    # Save Replies
    for r in all_replies:
        cid = contact_map.get(r['email'].lower())
        if cid:
            supabase.table('contacts').update({'status': 'replied'}).eq('id', cid).execute()
            if r['message_id']:
                exists = supabase.table('replies').select('id').eq('message_id', r['message_id']).execute()
                if exists.data: continue
            supabase.table('replies').insert({
                'contact_id': cid,
                'sender_email': r['email'],
                'recipient_email': r['recipient_email'],
                'subject': r['subject'],
                'body': r['body'][:5000], # Trucate extreme bodies
                'sentiment': r['sentiment'],
                'sentiment_score': r['sentiment_score'],
                'message_id': r['message_id'],
                'thread_id': r['thread_id']
            }).execute()

    return {"status": "completed", "replies": len(all_replies), "bounces": len(all_bounces)}

if __name__ == "__main__":
    check_replies()
