# 📄 Plagiarism & AI Detector — Telegram Bot

A **100% free** Telegram bot that analyses documents for:
- 🤖 AI-generated content (via Claude API)
- 🔍 Plagiarism (via DuckDuckGo web search — no API key needed)

Supports PDF, DOCX, and TXT files. Users can also paste text directly.

---

## ✅ Prerequisites

- Python 3.10+
- A Telegram Bot Token (free from [@BotFather](https://t.me/BotFather))
- An Anthropic API key (free tier available at [console.anthropic.com](https://console.anthropic.com))

---

## 🚀 Setup (5 minutes)

### 1. Clone / download the files
```bash
mkdir plagiarism_bot && cd plagiarism_bot
# Place bot.py and requirements.txt here
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get your Telegram Bot Token
1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456789:ABCdef...`)

### 4. Get your Anthropic API Key
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up / log in → API Keys → Create Key
3. Copy the key (starts with `sk-ant-...`)

### 5. Set environment variables
**Linux / macOS:**
```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=123456789:ABCdef...
set ANTHROPIC_API_KEY=sk-ant-...
```

**Or create a `.env` file** (add `python-dotenv` to requirements.txt):
```
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
ANTHROPIC_API_KEY=sk-ant-...
```

**Or just hard code the token and key in `bot.py` file** :
```
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
ANTHROPIC_API_KEY=sk-ant-...
```

### 6. Run the bot
```bash
python bot.py
```

---

## 🛠 Usage

| Action | How |
|--------|-----|
| Start the bot | Send `/start` in Telegram |
| Check a file | Upload a PDF, DOCX, or TXT |
| Check pasted text | Just type/paste the text |
| Help | Send `/help` |

---

## 📊 What the Report Includes

**AI Detection:**
- Probability score (0–100%)
- Verdict: Human-written / Likely AI / Definitely AI
- Confidence level
- Specific writing indicators detected
- Plain-English summary

**Plagiarism Check:**
- Up to 6 key sentences searched on the web
- Matching URLs and page titles
- Direct links to source pages

---

## 🔒 Running 24/7 (Optional)

### Option A — Free cloud: Railway.app
1. Push code to a GitHub repo
2. Connect repo to [railway.app](https://railway.app)
3. Add environment variables in Railway dashboard
4. Deploy — Railway keeps it running for free

### Option B — Free cloud: Render.com
1. Create a new **Background Worker** service
2. Connect your GitHub repo
3. Set env vars → Deploy

### Option C — VPS / local server with systemd
```ini
# /etc/systemd/system/plagiarism-bot.service
[Unit]
Description=Plagiarism & AI Detector Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/plagiarism_bot
Environment=TELEGRAM_BOT_TOKEN=xxx
Environment=ANTHROPIC_API_KEY=xxx
ExecStart=/usr/bin/python3 /home/ubuntu/plagiarism_bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable plagiarism-bot
sudo systemctl start plagiarism-bot
```

---

## ⚠️ Limitations

- **Plagiarism check** samples up to 6 sentences — it's not a full-database scan like Turnitin
- **AI detection** is probabilistic — treat scores as guidance, not ground truth
- **DuckDuckGo** may rate-limit heavy usage; add `time.sleep(1)` between searches if needed
- Scanned PDF images (no text layer) cannot be processed

---

## 💡 Extending the Bot

- Add more languages: Change the Claude prompt language
- Add a database: Store past reports with `sqlite3`
- Add `/stats` command: Track how many docs analysed
- Improve plagiarism: Integrate Copyleaks free tier (1,000 pages/month free)
