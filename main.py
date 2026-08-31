import os
import datetime
import feedparser
import pandas as pd
import resend
from google import genai

# ==========================================
# 1. CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RECIPIENT_EMAIL = "tenter.official@gmail.com"

resend.api_key = RESEND_API_KEY

RSS_FEEDS = {
    "Tech & AI": "https://news.ycombinator.com/rss",
    "World News": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Business & Markets": "https://search.cnbc.com/rs/search/combinedrender?target=partner&partnerId=2000&id=10000664&type=rss"
}

# ==========================================
# 2. FETCH NEWS FEEDS
# ==========================================
print("Fetching live news feeds...")
raw_news_data = ""
csv_records = []

for category, url in RSS_FEEDS.items():
    feed = feedparser.parse(url)
    raw_news_data += f"\n--- {category.upper()} ---\n"
    for entry in feed.entries[:3]:
        title = entry.title
        link = entry.link
        raw_news_data += f"- {title} ({link})\n"
        csv_records.append({
            "category": category,
            "headline": title,
            "source_url": link,
            "date": datetime.datetime.now().strftime("%Y-%m-%d")
        })

# ==========================================
# 3. GENERATE AI BRIEF (GOOGLE GENAI SDK)
# ==========================================
print("Generating AI Brief with Gemini...")
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = f"""
You are an executive news editor. Review the following raw news items:
{raw_news_data}

Write a concise Daily Executive Brief.

STRICT FORMATTING INSTRUCTIONS:
- Do NOT use Markdown syntax (do NOT use ###, **, or *).
- Return your output using pure, clean HTML tags only.
- Use <h2> for Category Headers (e.g., <h2>Global Security & Geopolitics</h2>).
- Use <ul> and <li> for news bullets.
- Wrap primary headlines inside <strong> tags (e.g., <li><strong>US-Iran Strikes Escalation:</strong> Military tension flared...</li>).
"""

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt
)
html_formatted_brief = response.text

# ==========================================
# 4. SAVE TXT BRIEF & APPEND CSV
# ==========================================
today = datetime.datetime.now().strftime("%Y-%m-%d")
os.makedirs("briefs", exist_ok=True)

with open(f"briefs/brief_{today}.txt", "w", encoding="utf-8") as f:
    f.write(f"DAILY EXECUTIVE NEWS BRIEF - {today}\n\n{html_formatted_brief}")

df_new = pd.DataFrame(csv_records)
if os.path.exists("news_archive.csv"):
    df_existing = pd.read_csv("news_archive.csv")
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_csv("news_archive.csv", index=False)
else:
    df_new.to_csv("news_archive.csv", index=False)

# ==========================================
# 5. DISPATCH EMAIL VIA RESEND
# ==========================================
print("Sending styled HTML email...")

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
  <div style="font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: 2px;">TENTER <span style="color: #38bdf8;">AI</span></div>
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

resend.Emails.send({
    "from": "onboarding@resend.dev",
    "to": RECIPIENT_EMAIL,
    "subject": f"📰 Tenter AI Morning Brief - {today}",
    "html": html_body
})

print("Daily brief generated and sent successfully!")
