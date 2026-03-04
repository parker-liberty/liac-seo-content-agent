"""
Liberty In a Can™ — SEO Content Agent
Runs daily via GitHub Actions. Writes a blog post + product copy per keyword.
Delivers plain text + Shopify-ready HTML email to parker@drinklic.com.

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
import re
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIG ──────────────────────────────────────────────────────────────────────────────

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

# ── MEMORY LAYER 1: Load brand voice from file ──────────────────────────────────────────────

def load_brand_voice() -> str:
    voice_path = Path("prompts/brand_voice.md")
    if voice_path.exists():
        return voice_path.read_text(encoding="utf-8")
    return (
        "You are a content writer for Liberty In a Can™ (LIC), maker of "
        "America's THC Seltzer™ and Liber-Tea™. Write confident, friendly, "
        "benefit-forward SEO content. No medical claims. Short punchy sentences."
    )

# ── MEMORY LAYER 2: Load approved samples ──────────────────────────────────────────────────────

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
    return f"""
## APPROVED OUTPUT EXAMPLES
The following are real approved outputs that match the LIC brand voice.
Study the tone, structure, and rhythm — replicate this quality:

{sample_text}

---
Now write new content for the keyword below at this same level of quality.
"""

# ── MEMORY LAYER 3: Output log ──────────────────────────────────────────────────────────────────────────────

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

# ── KEYWORD ROTATION ───────────────────────────────────────────────────────────────────────────────────

def get_todays_keyword() -> str:
    day_index = datetime.now().timetuple().tm_yday
    return KEYWORD_POOL[day_index % len(KEYWORD_POOL)]

# ── CONTENT GENERATION ────────────────────────────────────────────────────────────────────────────────

def generate_content(keyword: str) -> tuple[str, str]:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    brand_voice   = load_brand_voice()
    sample_inject = load_approved_samples(n=2)
    system_prompt = f"{brand_voice}\n\n{sample_inject}"
    user_prompt = f"""
Today's keyword: "{keyword}"

Please write TWO pieces of content:

## 1. SEO BLOG POST
- Follow the blog post structure in the brand voice guidelines
- 600-900 words
- Use H2/H3 subheadings
- End with a CTA including [LINK TO PRODUCT PAGE] placeholder
- Include meta description (150-160 chars) at the very end

## 2. PRODUCT PAGE COPY
- Short-form copy for the most relevant LIC product for this keyword
- Follow the product copy structure in the brand voice guidelines
- Include specs line and CTA

Separate the two pieces with: ===PRODUCT COPY===
"""
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2500,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )
    full_output = response.content[0].text
    if "===PRODUCT COPY===" in full_output:
        parts = full_output.split("===PRODUCT COPY===")
        return parts[0].strip(), parts[1].strip()
    return full_output, "(Product copy not separated — check output)"

# ── MARKDOWN TO HTML ────────────────────────────────────────────────────────────────────────────────

def markdown_to_shopify_html(blog_post: str, product_copy: str, keyword: str) -> str:
    """Convert markdown content to clean Shopify-pasteable HTML."""

    def md_to_html(text: str) -> str:
        lines = text.split("\n")
        html_lines = []
        in_para = False

        for line in lines:
            line = line.rstrip()

            # Skip meta description line (goes into Shopify SEO field separately)
            if line.lower().startswith("*meta description"):
                html_lines.append(f'<p><em><strong>META DESCRIPTION (paste into Shopify SEO field):</strong> {line.strip("*").strip()}</em></p>')
                continue

            if line.startswith("### "):
                if in_para: html_lines.append("</p>"); in_para = False
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                if in_para: html_lines.append("</p>"); in_para = False
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                if in_para: html_lines.append("</p>"); in_para = False
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("- ") or line.startswith("* "):
                if in_para: html_lines.append("</p>"); in_para = False
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line == "":
                if in_para: html_lines.append("</p>"); in_para = False
            elif "[LINK TO PRODUCT PAGE]" in line:
                if in_para: html_lines.append("</p>"); in_para = False
                cta_text = line.replace("[LINK TO PRODUCT PAGE]", "").strip()
                if not cta_text:
                    cta_text = "Shop Now"
                html_lines.append(
                    f'<p><a href="PASTE_PRODUCT_URL_HERE" style="display:inline-block;'
                    f'background-color:#1B2F5B;color:#ffffff;padding:14px 28px;'
                    f'text-decoration:none;border-radius:4px;font-weight:bold;'
                    f'font-size:16px;">{cta_text} →</a></p>'
                )
            else:
                # Apply inline formatting
                line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
                if not in_para:
                    html_lines.append("<p>")
                    in_para = True
                html_lines.append(line)

        if in_para:
            html_lines.append("</p>")

        return "\n".join(html_lines)

    blog_html    = md_to_html(blog_post)
    product_html = md_to_html(product_copy)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.7; }}
  h1 {{ color: #1B2F5B; font-size: 2em; margin-bottom: 0.3em; }}
  h2 {{ color: #1B2F5B; font-size: 1.4em; margin-top: 1.8em; border-bottom: 2px solid #6EC6A0; padding-bottom: 4px; }}
  h3 {{ color: #2a4a7f; font-size: 1.1em; margin-top: 1.4em; }}
  p {{ margin: 0.8em 0; }}
  li {{ margin: 0.4em 0; }}
  .section-divider {{ border: none; border-top: 3px solid #1B2F5B; margin: 40px 0; }}
  .product-copy {{ background: #f8f9ff; border-left: 4px solid #6EC6A0; padding: 24px; border-radius: 4px; }}
  .instructions {{ background: #fff8e1; border: 1px solid #ffc107; padding: 16px; border-radius: 4px; font-family: monospace; font-size: 13px; margin-bottom: 30px; }}
  .keyword-tag {{ display: inline-block; background: #1B2F5B; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; margin-bottom: 20px; }}
</style>
</head>
<body>

<div class="instructions">
✅ HOW TO USE THIS IN SHOPIFY<br>
1. Go to your Shopify admin → Online Store → Blog Posts → Add blog post<br>
2. Click the &lt;&gt; (HTML) button in the editor<br>
3. Paste ONLY the BLOG POST section below (between the hr tags)<br>
4. Replace PASTE_PRODUCT_URL_HERE with your actual product URL<br>
5. Scroll down to the SEO section and paste the META DESCRIPTION<br>
6. For product copy: use in your product description editor the same way
</div>

<span class="keyword-tag">Keyword: {keyword}</span>

<!-- ============================================================ -->
<!-- BLOG POST — paste this into Shopify blog post HTML editor   -->
<!-- ============================================================ -->

{blog_html}

<hr class="section-divider">

<!-- ============================================================ -->
<!-- PRODUCT COPY — paste into Shopify product description editor -->
<!-- ============================================================ -->

<div class="product-copy">
{product_html}
</div>

</body>
</html>"""

# ── EMAIL DELIVERY ─────────────────────────────────────────────────────────────────────────────────

def send_email(keyword: str, blog_post: str, product_copy: str):
    today = datetime.now().strftime("%B %d, %Y")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"U0001f5fd LIC SEO Content — {keyword} ({today})"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL

    # Plain text part
    plain_body = f"""LIC SEO CONTENT AGENT — {today}
Keyword: {keyword}

{'='*40}
BLOG POST
{'='*40}

{blog_post}


{'='*40}
PRODUCT COPY
{'='*40}

{product_copy}


{'='*40}
FEEDBACK
{'='*40}
Was this output on-brand? Reply with:
  APPROVED — add to approved_samples/
  REJECTED [note] — what was off
"""

    # HTML part (Shopify-ready)
    html_body = markdown_to_shopify_html(blog_post, product_copy, keyword)

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

    print(f"✅ Email sent to {RECIPIENT_EMAIL}")

# ── MAIN ───────────────────────────────────────────────────────────────────────────────────────

def main():
    keyword = os.environ.get("OVERRIDE_KEYWORD") or get_todays_keyword()
    print(f"U0001f5fd Running LIC SEO Agent | Keyword: {keyword}")
    print("U0001f4dd Generating content...")
    blog_post, product_copy = generate_content(keyword)
    print("U0001f4be Logging output...")
    log_output(keyword, blog_post, product_copy)
    print("U0001f4ec Sending email (plain + Shopify HTML)...")
    send_email(keyword, blog_post, product_copy)
    print("✅ Done.")

if __name__ == "__main__":
    main()
