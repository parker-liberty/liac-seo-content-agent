"""
Liberty In a Can - SEO Content Agent
Runs daily via GitHub Actions. Saves as Google Docs in Drive.
"""
import anthropic
import os
import json
import time
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

KEYWORD_POOL = [
    "THC seltzer Florida",
    "hemp drinks alcohol alternative",
    "THC beverages near me",
    "cannabis seltzer vs alcohol",
    "hemp THC drink review",
    "best THC drinks 2025",
    "sober curious drinks with THC",
    "THC tea Florida",
    "low dose THC drinks",
    "hemp infused seltzer",
    "alcohol alternative THC beverage",
    "social THC drink",
    "THC sparkling water",
    "hemp drink Tennessee",
    "cannabis beverage distribution",
]

BRAND_VOICE = """You are the official SEO copywriter for Liberty In a Can.
Liberty In a Can makes hemp-derived THC beverages: Liberty Seltzer and Liberty Tea (5mg and 10mg).
Distributed in Florida and Tennessee. Brand voice: American freedom, bold, witty, lifestyle-forward.
Never make health claims. Audience: adults 25-55, sober-curious, reducing alcohol.
Use plain text formatting. Use ALL CAPS for headings. Lead with primary keyword naturally in first 100 words."""


def pick_todays_keyword():
    override = os.environ.get("KEYWORD_OVERRIDE", "").strip()
    if override:
        return override
    day_of_year = datetime.now().timetuple().tm_yday
    return KEYWORD_POOL[day_of_year % len(KEYWORD_POOL)]


def call_with_retry(fn, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"Rate limit hit, waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait)
    raise Exception("Max retries exceeded")


def research_keyword(client, keyword):
    print(f"Researching: {keyword}")
    def _call():
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            system="You are an SEO research specialist for hemp THC beverages. Be concise.",
            messages=[{"role": "user", "content": f'Research SEO landscape for: "{keyword}". Return: search intent, top 5 LSI keywords, what top content covers, 3 content hooks. Keep it brief.'}]
        )
    response = call_with_retry(_call)
    research = "\n".join(block.text for block in response.content if block.type == "text")
    print(f"Research complete ({len(research.split())} words)")
    return research


def write_blog_post(client, keyword, research):
    print("Writing blog post...")
    time.sleep(30)
    def _call():
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=BRAND_VOICE,
            messages=[{"role": "user", "content": f"""Write a full SEO blog post (800-1000 words) targeting: "{keyword}"
Structure: TITLE (H1), 3-4 sections with SECTION HEADERS, conclusion, FAQ with 3 questions.
SEO Research: {research}
Use 2-3 related keywords naturally."""}]
        )
    response = call_with_retry(_call)
    content = response.content[0].text
    print(f"Blog post written ({len(content.split())} words)")
    return content


def write_product_copy(client, keyword, research):
    print("Writing product copy...")
    time.sleep(30)
    def _call():
        return client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=BRAND_VOICE,
            messages=[{"role": "user", "content": f"""Write SEO product page copy targeting: "{keyword}"
Include: HEADLINE, 3 benefit bullets, description (120-150 words), CTA, META TITLE (max 60 chars), META DESCRIPTION (max 160 chars).
SEO Research: {research}"""}]
        )
    response = call_with_retry(_call)
    content = response.content[0].text
    print(f"Product copy written ({len(content.split())} words)")
    return content


def get_drive_service():
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def save_as_google_doc(drive_service, title, content, folder_id=None):
    """Upload plain text and convert to Google Doc on import — no storage quota needed."""
    file_metadata = {
        "name": title,
        "mimeType": "application/vnd.google-apps.document"  # Convert to Google Doc
    }
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaInMemoryUpload(
        content.encode("utf-8"),
        mimetype="text/plain",
        resumable=False
    )
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,webViewLink"
    ).execute()
    url = file.get("webViewLink", f"https://docs.google.com/document/d/{file.get('id')}/edit")
    print(f"Saved Google Doc: {title}")
    print(f"  URL: {url}")
    return url


def run_agent():
    print("Liberty In a Can - SEO Agent Starting")
    print(datetime.now().strftime("%A, %B %d %Y at %I:%M %p"))
    print("-" * 50)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    keyword = pick_todays_keyword()
    print(f"Today's keyword: {keyword}")

    research = research_keyword(client, keyword)
    blog_post = write_blog_post(client, keyword, research)
    product_copy = write_product_copy(client, keyword, research)

    print("\nSaving to Google Drive as Google Docs...")
    drive_service = get_drive_service()
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder_id = GOOGLE_DRIVE_FOLDER_ID or None

    blog_text = f"KEYWORD: {keyword}\nDATE: {date_str}\n\n{'='*50}\n\n{blog_post}"
    save_as_google_doc(drive_service, f"LIAC Blog - {keyword} - {date_str}", blog_text, folder_id)

    product_text = f"KEYWORD: {keyword}\nDATE: {date_str}\n\n{'='*50}\n\n{product_copy}"
    save_as_google_doc(drive_service, f"LIAC Product Copy - {keyword} - {date_str}", product_text, folder_id)

    print("\nDone! Check your Google Drive LIAC SEO Content folder.")


if __name__ == "__main__":
    run_agent()
