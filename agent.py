"""
Liberty In a Can - SEO Content Agent
Runs daily via GitHub Actions. Saves markdown files to Google Drive.
"""
import anthropic
import os
import json
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
Use markdown formatting. Lead with primary keyword naturally in first 100 words."""


def pick_todays_keyword():
    override = os.environ.get("KEYWORD_OVERRIDE", "").strip()
    if override:
        return override
    day_of_year = datetime.now().timetuple().tm_yday
    return KEYWORD_POOL[day_of_year % len(KEYWORD_POOL)]


def research_keyword(client, keyword):
    print(f"Researching: {keyword}")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="You are an SEO research specialist for hemp THC beverages. Search for the keyword and return a structured brief with: search intent, top 5 LSI keywords, what top content covers, and content hooks.",
        messages=[{"role": "user", "content": f'Research SEO landscape for: "{keyword}". Focus on hemp THC beverages and alcohol alternatives.'}]
    )
    research = "\n".join(block.text for block in response.content if block.type == "text")
    print(f"Research complete ({len(research.split())} words)")
    return research


def write_blog_post(client, keyword, research):
    print("Writing blog post...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=BRAND_VOICE,
        messages=[{"role": "user", "content": f"""Write a full SEO blog post (800-1000 words) targeting: "{keyword}"

Structure: H1, 3-4 H2 sections, Conclusion, FAQ (3 Q&As)
SEO Research: {research}

Use 2-3 related keywords naturally."""}]
    )
    content = response.content[0].text
    print(f"Blog post written ({len(content.split())} words)")
    return content


def write_product_copy(client, keyword, research):
    print("Writing product copy...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=BRAND_VOICE,
        messages=[{"role": "user", "content": f"""Write SEO product page copy targeting: "{keyword}"

Structure: H1 headline, 3 benefit bullets, body paragraph (120-150 words), CTA, Meta Title (max 60 chars), Meta Description (max 160 chars)
SEO Research: {research}"""}]
    )
    content = response.content[0].text
    print(f"Product copy written ({len(content.split())} words)")
    return content


def get_drive_service():
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def save_to_drive(drive_service, filename, content, folder_id=None):
    file_metadata = {"name": filename, "mimeType": "text/plain"}
    if folder_id:
        file_metadata["parents"] = [folder_id]
    media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain")
    file = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()
    url = f"https://drive.google.com/file/d/{file.get('id')}/view"
    print(f"Saved: {filename} -> {url}")
    return url


def run_agent():
    print("Liberty In a Can - SEO Agent Starting")
    print(datetime.now().strftime("%A, %B %d %Y at %I:%M %p"))

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    keyword = pick_todays_keyword()
    print(f"Today's keyword: {keyword}")

    research = research_keyword(client, keyword)
    blog_post = write_blog_post(client, keyword, research)
    product_copy = write_product_copy(client, keyword, research)

    print("Saving to Google Drive...")
    drive_service = get_drive_service()
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_kw = keyword.replace(" ", "_").replace("/", "-")
    folder_id = GOOGLE_DRIVE_FOLDER_ID or None

    save_to_drive(drive_service,
        f"LIAC_Blog_{safe_kw}_{date_str}.md",
        f"# KEYWORD: {keyword}\n# DATE: {date_str}\n\n## RESEARCH\n\n{research}\n\n---\n\n## BLOG POST\n\n{blog_post}",
        folder_id)

    save_to_drive(drive_service,
        f"LIAC_ProductCopy_{safe_kw}_{date_str}.md",
        f"# KEYWORD: {keyword}\n# DATE: {date_str}\n\n---\n\n## PRODUCT COPY\n\n{product_copy}",
        folder_id)

    print("Done! Check your Google Drive folder.")


if __name__ == "__main__":
    run_agent()
