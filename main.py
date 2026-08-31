import os
import json
import resend
import feedparser
import pandas as pd
from datetime import datetime
import google.generativeai as genai

# ==========================================
# CONFIGURATION
# Reads keys directly from GitHub Secrets (or local fallback if testing locally)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_LOCAL_GEMINI_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_YOUR_LOCAL_RESEND_KEY")
RECIPIENT_EMAIL = "tenter.official@gmail.com" # Where you want to receive the email

# Setup API keys
os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
genai.configure()
resend.api_key = RESEND_API_KEY

# ==========================================
# 1. FETCH EXPANDED RSS FEEDS
# ==========================================
RSS_FEEDS = {
    "World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "Tech": "https://feeds.feedburner.com/TechCrunch/",
    "Sports": "http://feeds.bbci.co.uk/sport/rss.xml",
    "Crypto": "https://cointelegraph.com/rss"
}

print("Fetching live news feeds...")
raw_articles = []

for category, url in RSS_FEEDS.items():
    feed = feedparser.parse(url)
    for entry in feed.entries[:3]:  # Top 3 articles per category
        raw_articles.append({
            "category": category,
            "title": entry.title,
            "summary": getattr(entry, 'summary', ''),
            "link": entry.link,
            "published": getattr(entry, 'published', '')
        })

# ==========================================
# 2. GENERATE AI EXECUTIVE BRIEF
prompt = f"""
You are an executive news editor. Review the following raw news items:
{raw_news_data}

Write a concise Daily Executive Brief. 

STRICT FORMATTING INSTRUCTIONS:
- Do NOT use Markdown syntax (no ###, no **, no *).
- Return your output using pure, clean HTML tags only.
- Use <h2> for Category Headers (e.g., <h2>Global Security & Geopolitics</h2>).
- Use <ul> and <li> for news bullets.
- Wrap primary headlines inside <strong> tags (e.g., <li><strong>US-Iran Strikes Escalation:</strong> Military tension flared...</li>).
"""

response = model.generate_content(prompt)
html_formatted_brief = response.text

# ==========================================
# 3. SAVE TXT BRIEF & APPEND TO CSV
today = datetime.now().strftime("%Y-%m-%d")

# Create briefs directory if it does not exist
os.makedirs("briefs", exist_ok=True)

brief_filename = f"briefs/brief_{today}.txt"

with open(brief_filename, "w", encoding="utf-8") as f:
    f.write(f"DAILY EXECUTIVE NEWS BRIEF - {today}\n")
    f.write("=" * 40 + "\n\n")
    f.write(human_brief)

print(f"Saved human brief to: {brief_filename}")

parsed_data = json.loads(raw_json_str)
for item in parsed_data:
    item["date"] = today

df_new = pd.DataFrame(parsed_data)
csv_filename = "news_archive.csv"

if os.path.exists(csv_filename):
    df_new.to_csv(csv_filename, mode='a', header=False, index=False, encoding="utf-8-sig")
else:
    df_new.to_csv(csv_filename, mode='w', header=True, index=False, encoding="utf-8-sig")

print(f"Appended {len(parsed_data)} articles to: {csv_filename}")

# ==========================================
# 4. SEND EMAIL VIA RESEND
today = datetime.now().strftime("%Y-%m-%d")

subject = f"📰 Tenter AI Morning Brief - {today}"

html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      margin: 0; padding: 0; background-color: #f4f6f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }}
    .container {{
      max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }}
    .header {{
      background-color: #0f172a; padding: 24px; text-align: center;
    }}
    .logo {{
      max-width: 140px; height: auto; display: block; margin: 0 auto;
    }}
    .sub-header {{
      color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; font-weight: 600;
    }}
    .content {{
      padding: 30px 24px; color: #334155; line-height: 1.6; font-size: 15px;
    }}
    .date-badge {{
      display: inline-block; background: #e2e8f0; color: #475569; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-bottom: 20px;
    }}
    h2 {{
      color: #0f172a; font-size: 16px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-top: 24px; text-transform: uppercase;
    }}
    ul {{
      margin: 0 0 20px 0; padding-left: 20px;
    }}
    li {{
      margin-bottom: 12px;
    }}
    strong {{
      color: #0f172a;
    }}
    .footer {{
      background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="https://raw.githubusercontent.com/tenterofficial-lang/daily_news/main/logo.png" alt="Tenter AI" class="logo" />
      <div class="sub-header">Executive Daily Brief</div>
    </div>
    
    <div class="content">
      <div class="date-badge">📅 {today}</div>
      {html_formatted_brief}
    </div>
    
    <div class="footer">
      Generated automatically by Tenter AI Engine
    </div>
  </div>
</body>
</html>
"""

# Send via Resend
resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": RECIPIENT_EMAIL,
    "subject": subject,
    "html": html_body
})
