"""
Liberty In a Can - SEO Content Agent
Runs daily via GitHub Actions. Emails content to parker@drinklic.com.
"""
import anthropic
import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SMTP_EMAIL = os.environ["SMTP_EMAIL"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
TO_EMAIL = "parker@drinklic.com"

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
Use markdown formatting with # for H1, ## for H2, ** for bold, * for bullets.
Lead with primary keyword naturally in first 100 words."""


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
Structure: # H1 title, ## H2 sections (3-4), conclusion, ## Frequently Asked Questions (3 Q&As)
SEO Research: {research}
Use 2-3 related keywords naturally. Use markdown throughout."""}]
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
Structure: # H1 headline, ## Benefits (3 bullets), ## Description (120-150 words), ## Call to Action, **Meta Title:** (max 60 chars), **Meta Description:** (max 160 chars)
SEO Research: {research}"""}]
        )
    response = call_with_retry(_call)
    content = response.content[0].text
    print(f"Product copy written ({len(content.split())} words)")
    return content


def send_email(keyword, date_str, blog_post, product_copy):
    print("Sending email...")
    subject = f"🌿 LIAC Daily SEO Drop — {keyword} — {date_str}"
    html_body = f"""
<html><body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
<h1 style="color: #2d6a4f; border-bottom: 3px solid #2d6a4f; padding-bottom: 10px;">
    🌿 Liberty In a Can — Daily SEO Content
</h1>
<p><strong>Keyword:</strong> {keyword}<br><strong>Date:</strong> {date_str}</p>
<hr>
<h2 style="color: #1b4332;">📝 BLOG POST</h2>
<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; white-space: pre-wrap; font-size: 14px; line-height: 1.6;">{blog_post}</div>
<br><hr><br>
<h2 style="color: #1b4332;">🛒 PRODUCT COPY</h2>
<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; white-space: pre-wrap; font-size: 14px; line-height: 1.6;">{product_copy}</div>
<br>
<p style="color: #888; font-size: 12px;">Generated by LIAC SEO Agent</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, TO_EMAIL, msg.as_string())

    print(f"Email sent! Subject: {subject}")


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

    date_str = datetime.now().strftime("%Y-%m-%d")
    send_email(keyword, date_str, blog_post, product_copy)
    print("\nDone!")


if __name__ == "__main__":
    run_agent()
