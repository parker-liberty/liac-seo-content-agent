"""
Liberty In a Can - SEO Content Agent
Runs daily via GitHub Actions. Saves output as downloadable artifacts.
"""
import anthropic
import os
import time
from datetime import datetime

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")

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


def save_outputs(keyword, date_str, blog_post, product_copy):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_kw = keyword.replace(" ", "_").replace("/", "-")

    blog_file = os.path.join(OUTPUT_DIR, f"LIAC_Blog_{safe_kw}_{date_str}.md")
    with open(blog_file, "w") as f:
        f.write(f"# LIAC SEO Blog Post\n")
        f.write(f"**Keyword:** {keyword}  \n")
        f.write(f"**Date:** {date_str}\n\n---\n\n")
        f.write(blog_post)
    print(f"Saved: {blog_file}")

    product_file = os.path.join(OUTPUT_DIR, f"LIAC_ProductCopy_{safe_kw}_{date_str}.md")
    with open(product_file, "w") as f:
        f.write(f"# LIAC SEO Product Copy\n")
        f.write(f"**Keyword:** {keyword}  \n")
        f.write(f"**Date:** {date_str}\n\n---\n\n")
        f.write(product_copy)
    print(f"Saved: {product_file}")

    summary_file = os.path.join(OUTPUT_DIR, f"LIAC_Summary_{safe_kw}_{date_str}.md")
    with open(summary_file, "w") as f:
        f.write(f"# LIAC Daily SEO Drop — {keyword} — {date_str}\n\n")
        f.write(f"## Blog Post\n\n{blog_post}\n\n---\n\n")
        f.write(f"## Product Copy\n\n{product_copy}\n")
    print(f"Saved: {summary_file}")

    print(f"\n✅ All files saved to '{OUTPUT_DIR}/' folder")
    print(f"📥 Download them from the GitHub Actions run page under 'Artifacts'")


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
    save_outputs(keyword, date_str, blog_post, product_copy)
    print("\nDone!")


if __name__ == "__main__":
    run_agent()
