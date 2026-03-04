"""
Liberty In a Can™ — SEO Content Agent
Runs daily via GitHub Actions. Writes a blog post + product copy per keyword.
Delivers via email to parker@drinklic.com.

MEMORY ARCHITECTURE (3 layers):
  1. prompts/brand_voice.md    — Brand voice rules, loaded fresh every run
  2. approved_samples/         — Approved past outputs, 2 loaded randomly per run
  3. outputs_log.jsonl         — Running log of every output for feedback tracking
"""

import anthropic
import os
import json
import random
import smtplib
import glob
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

RECIPIENT_EMAIL = "parker@drinklic.com"
SENDER_EMAIL    = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD   = os.environ.get("SMTP_PASSWORD", "")
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")

KEYWORD_POOL = [
    "THC seltzer vs alcohol",
    "best THC drinks Florida",
    "hemp THC beverage benefits",
    "THC drinks Delray Beach",
    "full spectrum THC seltzer",
    "cannabis beverage alcohol alternative",
    "buy THC seltzer online",
    "low calorie cannabis drink",
    "hemp drink no hangover",
    "THC iced tea",
    "Delta 9 THC seltzer",
    "legal THC drink Florida",
    "social cannabis drink",
    "THC drink effects how long",
    "best hemp beverage 2025",
]


def load_brand_voice() -> str:
    voice_path = Path("prompts/brand_voice.md")
    if voice_path.exists():
        return voice_path.read_text(encoding="utf-8")
    return (
        "You are a content writer for Liberty In a Can™ (LIC), maker of "
        "America's THC Seltzer™ and Liber-Tea™. Write confident, friendly, "
        "benefit-forward SEO content. No medical claims. Short punchy sentences."
    )


def load_approved_samples(n: int = 2) -> str:
    sample_files = glob.glob("approved_samples/*.md")
    sample_files = [f for f in sample_files if "README" not in f]
    if not sample_files:
        return ""
    selected = random.sample(sample_files, min(n, len(sample_files)))
    blocks = []
    for path in selected:
        content = Path(path).read_text(encoding="utf-8")
        lines = content.split("\n")
        body_lines = [l for l in lines if not l.startswith("# ")]
        blocks.append("\n".join(body_lines).strip())
    sample_text = "\n\n---\n\n".join(blocks)
    return f"\n## APPROVED OUTPUT EXAMPLES\nStudy the tone and rhythm — replicate this quality:\n\n{sample_text}\n\n---\nNow write new content for the keyword below at this same level of quality.\n"


def log_output(keyword: str, blog_post: str, product_copy: str):
    log_path = Path("outputs_log.jsonl")
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "keyword": keyword,
        "blog_post_preview": blog_post[:300],
        "product_copy_preview": product_copy[:200],
        "approved": None,
        "notes": "",
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def get_todays_keyword() -> str:
    day_index = datetime.now().timetuple().tm_yday
    return KEYWORD_POOL[day_index % len(KEYWORD_POOL)]


def generate_content(keyword: str) -> tuple[str, str]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    brand_voice   = load_brand_voice()
    sample_inject = load_approved_samples(n=2)
    system_prompt = f"{brand_voice}\n\n{sample_inject}"
    user_prompt = f'''\nToday\'s keyword: "{keyword}"\n\nPlease write TWO pieces of content:\n\n## 1. SEO BLOG POST\n- Follow the blog post structure in the brand voice guidelines\n- 600-900 words\n- Use H2/H3 subheadings\n- End with a CTA including [LINK TO PRODUCT PAGE] placeholder\n- Include meta description (150-160 chars) at the very end\n\n## 2. PRODUCT PAGE COPY\n- Short-form copy for the most relevant LIC product for this keyword\n- Follow the product copy structure in the brand voice guidelines\n- Include specs line and CTA\n\nSeparate the two pieces with: ===PRODUCT COPY===\n'''
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2500,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )
    full_output = response.content[0].text
    if "===PRODUCT COPY===" in full_output:
        parts = full_output.split("===PRODUCT COPY===")
        return parts[0].strip(), parts[1].strip()
    return full_output, "(Product copy not separated — check output)"


def send_email(keyword: str, blog_post: str, product_copy: str):
    today = datetime.now().strftime("%B %d, %Y")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"LIC SEO Content — {keyword} ({today})"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    plain_body = f"LIC SEO CONTENT AGENT — {today}\nKeyword: {keyword}\n\n{'='*40}\nBLOG POST\n{'='*40}\n\n{blog_post}\n\n{'='*40}\nPRODUCT COPY\n{'='*40}\n\n{product_copy}\n\n{'='*40}\nFEEDBACK\n{'='*40}\nWas this output on-brand? Reply with:\n  APPROVED — to add to approved_samples/\n  REJECTED [note] — what was off\n\nApproved samples train the agent to improve over time."
    msg.attach(MIMEText(plain_body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
    print(f"✅ Email sent to {RECIPIENT_EMAIL}")


def main():
    keyword = os.environ.get("OVERRIDE_KEYWORD") or get_todays_keyword()
    print(f"U0001f5fd Running LIC SEO Agent | Keyword: {keyword}")
    print("U0001f4dd Generating content...")
    blog_post, product_copy = generate_content(keyword)
    print("U0001f4be Logging output...")
    log_output(keyword, blog_post, product_copy)
    print("U0001f4ec Sending email...")
    send_email(keyword, blog_post, product_copy)
    print("✅ Done.")


if __name__ == "__main__":
    main()
