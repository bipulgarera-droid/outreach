How to Self-Host Reacher.email (Beginner Guide)
This guide walks you step-by-step through installing Reacher.email on your own VPS so you can run high-accuracy email verification without paying per-credit SaaS fees.
No coding required. Just copy, paste, and click.
👉 Join AI Automation Insiders
🔗 https://leadgenjay.com/aia

Why Self-Hosting Reacher Matters
Most email verification tools give false positives because they can’t fully check SMTP servers.
Reacher is different because it:
Performs live SMTP verification
Requires outbound port 25 for best accuracy
Works best on a VPS that explicitly allows SMTP traffic
That’s why where you host this matters more than how you install it.

Step 0: Get the Right VPS (Important)
You must use a VPS provider that allows outbound port 25.
👉 Recommended (affiliate): HostCram
They allow port 25 and are friendly to email infrastructure.
🔗 Order your VPS here:
https://my.hostcram.com/order/forms/a/MzM0Mg==
What to select:
OS: Ubuntu 22.04 or 24.04
RAM: 2 GB minimum (4 GB recommended)
Save your IP address and root password
⚠️ Home computers and most ISPs block port 25. This will not work reliably on a desktop or home server.

Step 1: Log Into Your Server
On your Mac or Windows terminal:
ssh root@YOUR_VPS_IP

Type yes if prompted.

Step 2: Install Docker (One-Time Setup)
Copy and paste exactly:
apt update -y
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt update -y
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

Verify:
docker --version


Step 3: Create the Reacher Folder
mkdir -p /opt/reacher
cd /opt/reacher


Step 4: Create the Reacher App File
nano docker-compose.yml

Paste this (replace values as noted):
services:
  reacher:
    image: reacherhq/backend:latest
    container_name: reacher
    restart: unless-stopped
    environment:
      - RCH__API__SECRET=CHANGE_THIS_TO_A_LONG_RANDOM_STRING
      - RCH__HELLO_NAME=yourdomain.com
      - RCH__FROM_EMAIL=verify@yourdomain.com
    expose:
      - "8080"

  caddy:
    image: caddy:2
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - reacher

volumes:
  caddy_data:
  caddy_config:

Save with:
CTRL + O → Enter
CTRL + X

Step 5: Create HTTPS (Automatic SSL)
nano Caddyfile

Paste:
reacher.yourdomain.com {
  reverse_proxy reacher:8080
}

Save and exit.

Step 6: Point Your Domain
In Cloudflare or your DNS provider:
Type: A
Name: reacher
Value: YOUR_VPS_IP
Proxy: DNS only

Step 7: Open Firewall
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable


Step 8: Start Reacher
docker compose up -d
docker ps

Visit:
https://reacher.yourdomain.com

If it loads → you’re live.

Step 9: Verify Port 25 (Critical)
Run:
nc -vz gmail-smtp-in.l.google.com 25

If it says succeeded, your verification accuracy is maximized.

What You’ve Built (And Why This Matters)
You now have:
A private email verification API
No per-credit fees
Higher accuracy than most SaaS tools
Infrastructure you actually control
But this is just one piece of a full backend system.

🔥 Want to Build Full Apps Like This? (Recommended)
This Reacher setup is a real backend service — the same type of system used inside lead databases, AI tools, and automation platforms.
If you want to:
Use Claude Code to build full backend apps
Connect tools like n8n, Supabase, APIs, and web UIs
Turn setups like this into internal tools or paid SaaS
Stop guessing and follow real production patterns
👉 Join AI Automation Insiders
🔗 https://leadgenjay.com/aia
Inside, you’ll learn:
Claude Code workflows (non-developer friendly)
How to design backend systems like this from scratch
How to wire APIs, databases, automations, and frontends together
Real examples you can copy and adapt
This Reacher install is exactly the kind of system we break down step-by-step.

Summary
✔ Reacher installed
✔ High-accuracy email verification
✔ Port 25 unlocked
✔ Secure HTTPS endpoint
✔ Foundation for real backend apps
If you want help extending this (adding dashboards, credit systems, forms, or automations), that’s exactly what AI Automation Insiders is built for.
If you want, I can also:
Add rate-limiting
Connect this to n8n
Add a frontend UI
Turn it into a paid verification service

