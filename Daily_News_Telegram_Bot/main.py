import os
import re
import html
import time
import hmac
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

IST = ZoneInfo("Asia/Kolkata")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

TELEGRAM_URL = "https://api.telegram.org/bot{}/sendMessage"

FEEDS = [
    ("WIRED", "https://www.wired.com/feed/rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    (
        "Bloomberg Technology",
        "https://feeds.bloomberg.com/technology/news.rss",
    ),
]

ARTICLES_PER_SOURCE = 5
TELEGRAM_MESSAGE_LIMIT = 3500


# --------------------------------------------------
# TEXT CLEANING
# --------------------------------------------------

def clean_text(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------
# ARTICLE PUBLICATION DATE
# --------------------------------------------------

def get_article_date(entry):
    for key in ("published", "updated"):
        try:
            date = parsedate_to_datetime(entry[key])

            if date.tzinfo is None:
                date = date.replace(tzinfo=ZoneInfo("UTC"))

            return date.astimezone(IST)

        except (KeyError, ValueError, TypeError):
            continue

    return None


# --------------------------------------------------
# FETCH RSS ARTICLES
# --------------------------------------------------

def fetch_articles(source, feed_url):
    response = requests.get(
        feed_url,
        headers={
            "User-Agent": "DailyNewsDigest/1.0"
        },
        timeout=30,
    )

    response.raise_for_status()

    feed = feedparser.parse(response.content)

    articles = []

    for entry in feed.entries:
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "")

        if not title or not link:
            continue

        content = entry.get("summary", "")

        if entry.get("content"):
            content = entry["content"][0].get(
                "value",
                content
            )

        article = {
            "source": source,
            "title": title,
            "link": link,
            "date": get_article_date(entry),
            "excerpt": clean_text(content)[:10000],
        }

        articles.append(article)

    # Newest published articles first.
    articles.sort(
        key=lambda article: (
            article["date"]
            or datetime.min.replace(tzinfo=IST)
        ),
        reverse=True,
    )

    return articles[:ARTICLES_PER_SOURCE]


# --------------------------------------------------
# GENERATE APPROXIMATELY 75-WORD SUMMARY
# --------------------------------------------------

def summarize_article(article):
    prompt = f"""
You are a professional technology, AI, business,
finance, and startup news editor.

Write an informative summary of approximately
75 words for this news story.

STRICT RULES:

1. Explain the main development clearly.
2. Include important facts, figures, and names.
3. Explain what happened and why it matters.
4. Use simple, natural, understandable English.
5. Write one connected paragraph.
6. Aim for 70-85 words.
7. Do not use bullet points.
8. Do not include URLs or links.
9. Do not repeat the headline.
10. Do not add labels such as "Summary:".
11. Never invent facts or unsupported details.
12. Do not present speculation as confirmed news.
13. If the available information is insufficient,
    clearly acknowledge the limitation.

Publisher: {article['source']}

Headline:
{article['title']}

Available article text:
{article['excerpt']}

Return ONLY the summary paragraph.
"""

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": (
                f"Bearer {os.environ['GROQ_API_KEY']}"
            ),
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful news editor. "
                        "Write accurate, informative summaries "
                        "in simple English. Never fabricate facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
            "max_tokens": 220,
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"].strip()


# --------------------------------------------------
# FORMAT ONE STORY
# --------------------------------------------------

def format_story(article, story_number):
    title = html.escape(article["title"])

    try:
        summary = summarize_article(article)

    except Exception:
        app.logger.exception(
            "Summary generation failed for: %s",
            article["title"],
        )

        summary = (
            "A detailed summary could not be generated "
            "from the available information. "
            "The story requires further review."
        )

    summary = html.escape(summary)

    return (
        f"<b>Story {story_number} – {title}</b>\n\n"
        f"{summary}"
    )


# --------------------------------------------------
# SPLIT TELEGRAM MESSAGES SAFELY
# --------------------------------------------------

def split_messages(text, limit=TELEGRAM_MESSAGE_LIMIT):
    messages = []
    current = ""

    for paragraph in text.split("\n"):
        candidate = (
            f"{current}\n{paragraph}"
            if current
            else paragraph
        )

        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            messages.append(current)
            current = ""

        # Normally unnecessary, but prevents oversized paragraphs.
        while len(paragraph) > limit:
            messages.append(paragraph[:limit])
            paragraph = paragraph[limit:]

        current = paragraph

    if current:
        messages.append(current)

    return messages


# --------------------------------------------------
# SEND FORMATTED DIGEST TO TELEGRAM
# --------------------------------------------------

def send_telegram(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = TELEGRAM_URL.format(token)

    messages = split_messages(text)

    for message in messages:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise RuntimeError(
                f"Telegram API error: {result}"
            )

        time.sleep(0.5)


# --------------------------------------------------
# GENERATE COMPLETE DAILY NEWS DIGEST
# --------------------------------------------------

def generate_digest():
    today = datetime.now(IST).strftime("%d %B %Y")

    sections = [
        f"🗞️ <b>DAILY NEWS DIGEST</b>",
        f"📅 {today}",
        (
            "AI/ML • Technology • Business • "
            "Finance • Startups"
        ),
    ]

    story_number = 0
    total_articles = 0

    for source, feed_url in FEEDS:

        sections.extend([
            "",
            "━━━━━━━━━━━━━━━━━━",
            f"📌 <b>{html.escape(source.upper())}</b>",
            "━━━━━━━━━━━━━━━━━━",
        ])

        try:
            articles = fetch_articles(
                source,
                feed_url
            )

        except Exception:
            app.logger.exception(
                "Failed to fetch RSS feed: %s",
                source,
            )

            sections.append(
                "Unable to retrieve articles from this source today."
            )

            continue

        if not articles:
            sections.append(
                "No articles were available from this source."
            )

            continue

        for article in articles:
            story_number += 1

            story = format_story(
                article,
                story_number
            )

            sections.extend([
                "",
                story,
                "",
                "──────────────────",
            ])

            total_articles += 1

    sections.extend([
        "",
        f"✅ <b>Total Stories: {total_articles}</b>",
        "End of Daily News Digest.",
    ])

    digest = "\n".join(sections)

    send_telegram(digest)

    app.logger.info(
        "News digest sent successfully. Articles: %s",
        total_articles,
    )


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "status": "News bot is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# --------------------------------------------------
# SECURE SCHEDULED EXECUTION ENDPOINT
# --------------------------------------------------

@app.post("/run")
def run_news():
    secret = os.environ.get("RUN_SECRET", "")
    supplied = request.headers.get("X-Run-Secret", "")

    if (
        not secret
        or not supplied
        or not hmac.compare_digest(secret, supplied)
    ):
        return jsonify({
            "error": "Unauthorized"
        }), 401

    try:
        generate_digest()

        return jsonify({
            "status": "News digest sent successfully"
        }), 200

    except Exception:
        app.logger.exception(
            "News digest generation failed"
        )

        return jsonify({
            "error": (
                "Digest generation failed. "
                "Check Render logs."
            )
        }), 500


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )