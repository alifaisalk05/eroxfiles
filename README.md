# 🚀 ANIZONEFLIX Media Streamer

High-speed Telegram media streaming and direct link generator service.

made by anizoneflix

## ✨ Features

- ⚡ **Maximum Speed**: Optimized Telegram media streaming and direct link generation.
- 📱 **Clean UI**: Simple, clean, and fast web interface.
- 🔊 **Multi-Audio Remuxing**: Switch audio tracks on supported videos.
- 🎬 **External Player Support**: Stream directly in VLC, MX Player, MPV, and more.
- 🔒 **Force Subscribe & Security**: Access control and rate limiting.

---

## 🖥️ Complete VPS Ubuntu Deployment Guide

Follow this step-by-step guide from scratch to deploy the bot on an Ubuntu VPS.

### Step 1: Connect to Your VPS
Open your terminal or SSH client and log in to your Ubuntu VPS server:
```bash
ssh root@YOUR_VPS_IP
```

---

### Step 2: Update and Upgrade System Packages
Update your Ubuntu package repository and upgrade existing system packages to the latest versions:
```bash
sudo apt update && sudo apt upgrade -y
```

---

### Step 3: Install Required System Dependencies
Install Python 3, pip, venv, Git, FFmpeg, Nginx, and Certbot for SSL:
```bash
sudo apt install -y python3 python3-pip python3-venv git ffmpeg nginx certbot python3-certbot-nginx
```
**After this step**: Verify installations by running:
```bash
ffmpeg -version
python3 --version
nginx -v
```

---

### Step 4: Clone the Repository
Clone the repository into `/var/www/FileToLink` and navigate into the directory:
```bash
sudo git clone https://github.com/ANIZONEFLIX/FileToLink.git /var/www/FileToLink
cd /var/www/FileToLink
```

---

### Step 5: Create and Activate Virtual Environment
Set up an isolated Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
**After this step**: Your command prompt will show `(venv)` indicating the virtual environment is active.

---

### Step 6: Install Python Dependencies
Upgrade `pip` and install all required Python libraries from `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 7: Configure Environment Variables (`.env`)
Create a `.env` file in the project root directory:
```bash
nano .env
```

Paste and fill in your details:
```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
DATABASE_URL=mongodb+srv://your_mongo_db_url
BASE_URL=http://YOUR_VPS_IP
FORCE_SUB_CHANNELS=-100123456789
CHANNEL_ID=-100123456789
USER_SESSIONS=string_session1,string_session2
PORT=8000
```

#### 📌 How to set `BASE_URL` at each stage:
- **Stage 1 (Initial IP Testing without Domain)**: Set `BASE_URL=http://YOUR_VPS_IP` (e.g., `http://123.45.67.89`).
- **Stage 2 (HTTP Domain Proxy)**: If using a domain before SSL, set `BASE_URL=http://yourdomain.com`.
- **Stage 3 (Final Production with HTTPS/SSL)**: After completing Step 11 (Certbot SSL), update `.env` to `BASE_URL=https://yourdomain.com` and restart the service.

Save and exit `nano` (`Ctrl + O`, `Enter`, then `Ctrl + X`).

---

### Step 8: Configure Systemd Background Service
Create a systemd service file to keep the application running continuously in the background and auto-restart on system boot:

```bash
sudo nano /etc/systemd/system/anizoneflix.service
```

Add the following content:
```ini
[Unit]
Description=ANIZONEFLIX Media Streamer FastAPI Service
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/FileToLink
ExecStart=/var/www/FileToLink/venv/bin/python -m app.main
Restart=always
RestartSec=3
Environment=PORT=8000

[Install]
WantedBy=multi-user.target
```

Save and exit (`Ctrl + O`, `Enter`, `Ctrl + X`).

Now reload systemd, enable the service on boot, and start it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable anizoneflix
sudo systemctl start anizoneflix
```

Check service status:
```bash
sudo systemctl status anizoneflix
```

---

### Step 9: Configure Nginx Reverse Proxy
Create an Nginx server block configuration file:

```bash
sudo nano /etc/nginx/sites-available/anizoneflix
```

Add the following configuration (replace `yourdomain.com` with your actual domain name, or use your VPS IP if you don't have a domain yet):

```nginx
server {
    listen 80;
    server_name yourdomain.com; # Or YOUR_VPS_IP

    client_max_body_size 0;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

Enable the Nginx site configuration by creating a symbolic link:
```bash
sudo ln -s /etc/nginx/sites-available/anizoneflix /etc/nginx/sites-enabled/
```

Remove default Nginx configuration if present:
```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Test Nginx configuration for syntax errors:
```bash
sudo nginx -t
```

Restart Nginx:
```bash
sudo systemctl restart nginx
```

---

### Step 10: Configure Firewall (UFW)
Allow SSH, HTTP, and HTTPS traffic through the firewall:
```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

### Step 11: Setup Free SSL Certificate with Certbot
If you have pointed your domain DNS A Record to `YOUR_VPS_IP`, generate a free Let's Encrypt SSL certificate:

```bash
sudo certbot --nginx -d yourdomain.com
```

Follow the on-screen prompts. Certbot will automatically configure Nginx to use HTTPS.

**After SSL Installation**: Update your `.env` file:
```bash
nano /var/www/FileToLink/.env
```
Change `BASE_URL` to HTTPS:
```env
BASE_URL=https://yourdomain.com
```

Restart the service to apply the updated `BASE_URL`:
```bash
sudo systemctl restart anizoneflix
```

---

### Step 12: Test and Verify Deployment
1. Open `https://yourdomain.com` (or `http://YOUR_VPS_IP`) in your web browser.
2. Send a video file to your Telegram Bot.
3. Verify that the generated stream and download direct links work cleanly at maximum speed!

---
made by anizoneflix
