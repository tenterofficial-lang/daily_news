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
# 2. GENERATE AI SUMMARY & DATA
# ==========================================
model = genai.GenerativeModel('gemini-3.6-flash')

prompt = f"""
You are an executive news editor. Review these raw news entries:
{json.dumps(raw_articles, indent=2)}

Provide TWO outputs in your response:

SECTION 1: MORNING BRIEF
Write a clean, professional, readable executive summary of today's key stories formatted in markdown text.

SECTION 2: JSON DATA
Provide a valid raw JSON array of objects representing each article with these exact keys:
"category", "headline", "ai_takeaway", "source_url"

Separate SECTION 1 and SECTION 2 using exact boundary delimiter: ===JSON_START===
Do not include markdown code block backticks inside the JSON section.
"""

response = model.generate_content(prompt)

full_text = response.text.strip()
parts = full_text.split("===JSON_START===")

human_brief = parts[0].replace("SECTION 1: MORNING BRIEF", "").strip()
raw_json_str = parts[1].replace("SECTION 2: JSON DATA", "").replace("```json", "").replace("```", "").strip()

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
# 4. SEND EMAIL DISPATCH VIA RESEND
# ==========================================
print("Sending branded morning brief to email...")

# Replace with your direct hosted image link
LOGO_URL = "https://i.imgur.com/cnOXzmS.png"  

# Convert markdown headers/bullets into styled HTML cards
formatted_brief = human_brief.replace('\n', '<br>')

html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
      background-color: #0f172a;
      color: #e2e8f0;
      margin: 0;
      padding: 20px;
    }}
    .container {{
      max-width: 600px;
      margin: 0 auto;
      background-color: #1e293b;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #334155;
    }}
    .header {{
      background-color: #000000;
      padding: 25px;
      text-align: center;
      border-bottom: 2px solid #00f2fe;
    }}
    .header img {{
      max-width: 220px;
      height: auto;
    }}
    .content {{
      padding: 30px;
      line-height: 1.6;
      color: #cbd5e1;
    }}
    .footer {{
      background-color: #0f172a;
      padding: 15px;
      text-align: center;
      font-size: 12px;
      color: #64748b;
      border-top: 1px solid #334155;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <img src="{LOGO_URL}" alt="Tenter AI Logo">
    </div>
    <div class="content">
      <h2 style="color: #ffffff; margin-top: 0;">Daily Executive Brief</h2>
      <p style="color: #94a3b8; font-size: 14px;">Date: {today}</p>
      <hr style="border: 0; border-top: 1px solid #334155; margin: 20px 0;">
      <div>
        {formatted_brief}
      </div>
    </div>
    <div class="footer">
      <p>© 2026 Tenter AI • Automated Intelligence Services</p>
    </div>
  </div>
</body>
</html>
"""

email_params = {
    "from": "Tenter AI <onboarding@resend.dev>",
    "to": [RECIPIENT_EMAIL],
    "subject": f"⚡ Tenter AI Morning Brief - {today}",
    "html": html_body
}

try:
    email_response = resend.Emails.send(email_params)
    print("Branded email sent successfully! ID:", email_response)
except Exception as e:
    print("Failed to send email:", e)
