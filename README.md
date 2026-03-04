# 🗽 Liberty In a Can — SEO Content Agent

Runs automatically every morning. Researches a keyword, writes a blog post + product page copy, saves both to Google Drive. Zero input required.

---

## How It Works

1. **Picks a keyword** from a rotating pool (cycles daily so you never repeat)
2. **Researches** the keyword using live web search — competitor content, search intent, LSI keywords
3. **Writes** a full SEO blog post (800-1000 words) + product page copy in your brand voice
4. **Saves** both as Google Docs in your Drive folder

Runs every day at 7am ET. Can also be triggered manually from GitHub in seconds.

---

## Setup (15 minutes total)

### Step 1 — Create a new GitHub repo
1. Go to github.com → New repository → name it `liac-seo-agent`
2. Upload all files from this folder (preserving the `.github/workflows/` folder)

### Step 2 — Add your secrets in GitHub
Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 3 secrets:

| Secret Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON contents of your Google service account key file |
| `GOOGLE_DRIVE_FOLDER_ID` | ID of your Google Drive folder (from the URL) |

### Step 3 — Set up Google Drive access
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **Google Docs API** and **Google Drive API**
3. Go to **IAM & Admin** → **Service Accounts** → Create one
4. Download the JSON key file
5. Paste the entire JSON contents as the `GOOGLE_SERVICE_ACCOUNT_JSON` secret
6. Create a folder in Google Drive → Share it with the service account email (Editor access)
7. Copy the folder ID from the Drive URL and add as `GOOGLE_DRIVE_FOLDER_ID`

### Step 4 — Run it
**Automatic:** It runs every morning at 7am ET. Check your Drive folder.

**Manual trigger:**
1. Go to your GitHub repo → **Actions** tab
2. Click **LIAC SEO Agent** → **Run workflow**
3. Optionally type a specific keyword to override the daily rotation
4. Click **Run workflow** — done in ~60 seconds

---

## Customizing Keywords

Edit the `KEYWORD_POOL` list in `agent.py` to add your own keywords. The agent cycles through them by day so every day is a fresh topic.

## Customizing Brand Voice

Edit the `BRAND_VOICE` string in `agent.py` to update tone, product details, or SEO rules.

---

## Cost

- **GitHub Actions:** Free (2,000 minutes/month on free plan — this uses ~2 min/day)
- **Anthropic API:** ~$0.05-0.10 per run
- **Google APIs:** Free
