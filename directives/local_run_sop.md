# Outreach App — Local Run SOP

> Foolproof step-by-step to run the outreach platform on your Mac.

---

## One-Time Setup (First Time Only)

### 1. Install Python (if not already)
```bash
brew install python3
```

### 2. Install Dependencies
```bash
cd "/Users/bipul/Downloads/ALL WORKSPACES/festivals outreach"
pip3 install -r requirements.txt
```

### 3. Verify your `.env` file has these keys
Open `/Users/bipul/Downloads/ALL WORKSPACES/festivals outreach/.env` and confirm:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
PERPLEXITY_API_KEY=your_perplexity_key
GEMINI_API_KEY=your_gemini_key
GMAIL_1_EMAIL=your_email@gmail.com
GMAIL_1_PASSWORD=your_app_password
GMAIL_2_EMAIL=...
GMAIL_2_PASSWORD=...
```
(You should already have all of these set.)

---

## Daily Workflow

### Step 1: Open Terminal

Press `Cmd + Space`, type **Terminal**, hit Enter.

### Step 2: Start the Dashboard

Copy and paste this entire block:
```bash
cd "/Users/bipul/Downloads/ALL WORKSPACES/festivals outreach" && python3 -m gunicorn api.index:app --timeout 300 -b 127.0.0.1:5001
```

You'll see output like:
```
[INFO] Booting worker with pid: 12345
[INFO] Supabase client initialized
```

### Step 3: Open the Dashboard

Open your browser and go to:
```
http://127.0.0.1:5001
```

Your full dashboard is now live — manage contacts, templates, projects, everything.

### Step 4: Send Emails (Pick ONE method)

**Method A: Click the button (easiest)**
1. Go to the **Sequences** tab
2. Click the purple **"Run Daily Send"** button
3. Wait for the summary popup (1-2 hours for 250 emails)

**Method B: Run from Terminal (if you prefer)**

Open a **second Terminal tab** (`Cmd + T`) and paste:
```bash
cd "/Users/bipul/Downloads/ALL WORKSPACES/festivals outreach" && python3 -m execution.daily_run
```

This does everything: checks replies + sends pending emails.

**Useful flags:**
```bash
# Preview mode (see what WOULD send, without actually sending)
python3 -m execution.daily_run --dry-run

# Send max 100 emails instead of 250
python3 -m execution.daily_run --limit 100

# Slower sending (60-90s between emails for extra safety)
python3 -m execution.daily_run --delay-min 60 --delay-max 90
```

### Step 5: Done — Close When Finished

When the daily run finishes:
1. Go back to the Terminal running the server
2. Press `Ctrl + C` to stop it
3. Close Terminal

---

## Quick Reference

| Task | Where |
|------|-------|
| Add/manage contacts | Dashboard → Contacts tab |
| Create a new project | Dashboard → Projects dropdown → New Project |
| Edit email templates | Dashboard → Templates tab |
| Generate sequences for contacts | Dashboard → Contacts tab → Select contacts → Create Sequences |
| Send pending emails | Dashboard → Sequences tab → Run Daily Send |
| Test deliverability | Dashboard → Sequences tab → Test Workflow |
| Check for replies | Dashboard → Sequences tab → Check Replies |

---

## Troubleshooting

**"Address already in use" error:**
Another server is running on port 5001. Either close it or use a different port:
```bash
python3 -m gunicorn api.index:app --timeout 300 -b 127.0.0.1:5002
```

**"No Gmail accounts found" error:**
Your `.env` file is missing `GMAIL_1_EMAIL` and `GMAIL_1_PASSWORD`. Add them.

**"ModuleNotFoundError" error:**
Run `pip3 install -r requirements.txt` again.

**Emails not sending:**
Run with `--dry-run` first to check if sequences are queued. If the dry run shows 0 emails, you need to create sequences for your contacts first (Contacts tab → select → Create Sequences).
