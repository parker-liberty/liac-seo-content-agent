"""
Liberty In a Can — SEO Content Agent
Runs daily via GitHub Actions or manually.
Researches keywords, writes blog + product copy, saves to Google Drive.
"""

import anthropic
import os
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Config ─────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

# Keywords the agent cycles through — add more anytime
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

BRAND_VOICE = """You are the official SEO copywriter for Liberty In a Can — America's social alternative to alcohol.

COMPANY: Liberty In a Can makes hemp-derived THC beverages: Liberty Seltzer (5mg, 10mg) and Liberty Tea (5mg, 10mg). 
Distributed in Florida and Tennessee via Anheuser-Busch's Southern Eagle network.

BRAND VOICE:
- American freedom, pursuit of happiness, bold independence  
- Anti-establishment but approachable — craft beer meets craft cannabis
- Never preachy. Never stiff. Light, confident, witty.
- "Liberty" is the north star word
- Lifestyle-forward: social settings, celebration, relaxation, freedom from hangover
- Audience: adults 25-55, sober-curious, reducing alcohol
- NEVER make health claims or medical statements

SEO RULES:
- Lead with primary keyword naturally in first 100 words
- Use keyword 2-4x throughout (never stuffed)
- Include 2-3 semantic/LSI related keywords
- Blog posts: H2s every 200-300 words, FAQ section at end (3 questions)
- Product copy: benefit-first, sensory details, end with CTA
- Use markdown formatting throughout"""


# ── Keyword Selection ───────────────────────────────────────────────────────────

def pick_todays_keyword():
    """Rotate through keywords based on day of year so we never repeat."""
    day_of_year = datetime.now().timetuple().tm_yday
    keyword = KEYWORD_POOL[day_of_year % len(KEYWORD_POOL)]
    print(f"📍 Today's keyword: {keyword}")
    return keyword


# ── Research Phase ──────────────────────────────────────────────────────────────

def research_keyword(client, keyword):
    """Use Claude with web search to research the keyword landscape."""
    print(f"🔍 Researching: {keyword}")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="""You are an SEO research specialist focused on the hemp THC beverage and alcohol alternative industry.
Search for the provided keyword and return a structured research brief with:
- Search intent (what is the user looking for?)
- Top 3-5 related/LSI keywords to weave in naturally  
- What top-ranking content covers (gaps we can fill)
- Competitor angles to differentiate from
- 1-2 content hooks that would make our piece stand out
Be concise and actionable.""",
        messages=[{
            "role": "user",
            "content": f'Research the SEO landscape for: "{keyword}". Focus on hemp THC beverages, cannabis drinks, and alcohol alternatives.'
        }]
    )

    research = "\n".join(
        block.text for block in response.content if block.type == "text"
    )
    print(f"✅ Research complete ({len(research.split())} words)")
    return research


# ── Writing Phase ───────────────────────────────────────────────────────────────

def write_blog_post(client, keyword, research):
    """Write a full SEO blog post using research."""
    print(f"✍️  Writing blog post...")

    prompt = f"""Write a full SEO blog post (800-1000 words) targeting the keyword: "{keyword}"

Structure:
- Compelling H1 title (include keyword naturally)
- Intro paragraph that hooks the reader and includes the keyword in first 100 words
- 3-4 H2 sections with rich body copy (200-300 words each)
- Conclusion paragraph
- ## Frequently Asked Questions (3 questions with detailed answers)

SEO RESEARCH BRIEF — use this to inform your writing:
{research}

Use the research to naturally include 2-3 related keywords, address search intent, and fill content gaps."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=BRAND_VOICE,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.content[0].text
    print(f"✅ Blog post written ({len(content.split())} words)")
    return content


def write_product_copy(client, keyword, research):
    """Write SEO product page copy."""
    print(f"🛒  Writing product page copy...")

    prompt = f"""Write SEO-optimized product page copy targeting the keyword: "{keyword}"

Structure:
- Punchy H1 headline (keyword included naturally)
- 3 benefit bullets (benefit-first, sensory language)
- Body paragraph (120-150 words, descriptive, lifestyle-forward)  
- Strong CTA sentence
- Meta Title (max 60 chars, include keyword)
- Meta Description (max 160 chars, soft CTA)

SEO RESEARCH BRIEF:
{research}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=BRAND_VOICE,
        messages=[{"role": "user", "content": prompt}]
    )

    content = response.content[0].text
    print(f"✅ Product copy written ({len(content.split())} words)")
    return content


# ── Google Drive ────────────────────────────────────────────────────────────────

def get_drive_service():
    """Authenticate with Google Drive using service account."""
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    return docs_service, drive_service


def save_to_drive(docs_service, drive_service, title, content, folder_id=None):
    """Create a Google Doc and save content to it."""
    # Create the doc
    doc = docs_service.documents().create(
        body={"title": title}
    ).execute()
    doc_id = doc["documentId"]

    # Insert content
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]}
    ).execute()

    # Move to folder if specified
    if folder_id:
        drive_service.files().update(
            fileId=doc_id,
            addParents=folder_id,
            removeParents="root",
            fields="id, parents"
        ).execute()

    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"📄 Saved: {title}")
    print(f"   → {doc_url}")
    return doc_url


# ── Main Agent ──────────────────────────────────────────────────────────────────

def run_agent():
    print("\n🗽 Liberty In a Can — SEO Agent Starting")
    print(f"   {datetime.now().strftime('%A, %B %d %Y at %I:%M %p')}")
    print("─" * 50)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Pick keyword
    keyword = pick_todays_keyword()

    # Research
    research = research_keyword(client, keyword)

    # Write content
    blog_post = write_blog_post(client, keyword, research)
    product_copy = write_product_copy(client, keyword, research)

    # Save to Google Drive
    print("\n📁 Saving to Google Drive...")
    docs_service, drive_service = get_drive_service()

    date_str = datetime.now().strftime("%b %d %Y")
    folder_id = GOOGLE_DRIVE_FOLDER_ID or None

    blog_url = save_to_drive(
        docs_service, drive_service,
        title=f"LIAC SEO | Blog | {keyword} | {date_str}",
        content=f"KEYWORD: {keyword}\nDATE: {date_str}\n\nRESEARCH BRIEF:\n{research}\n\n{'─'*50}\n\nBLOG POST:\n\n{blog_post}",
        folder_id=folder_id
    )

    product_url = save_to_drive(
        docs_service, drive_service,
        title=f"LIAC SEO | Product Copy | {keyword} | {date_str}",
        content=f"KEYWORD: {keyword}\nDATE: {date_str}\n\n{'─'*50}\n\nPRODUCT PAGE COPY:\n\n{product_copy}",
        folder_id=folder_id
    )

    print("\n✅ Agent complete!")
    print(f"   Blog post  → {blog_url}")
    print(f"   Product    → {product_url}")
    print("─" * 50)


if __name__ == "__main__":
    run_agent()
