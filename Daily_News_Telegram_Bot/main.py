import os
import html
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

IST = ZoneInfo("Asia/Kolkata")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

FEEDS = [
    ("WIRED", "https://www.wired.com/feed/rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Bloomberg Technology",
     "https://feeds.bloomberg.com/technology/news.rss"),
]

def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def get_date(entry):
    for key in ("published", "updated"):
        try:
            return parsedate_to_datetime(entry[key]).astimezone(IST)
        except (KeyError, ValueError, TypeError):
            pass
    return None


def fetch_articles(source, url):
    feed = feedparser.parse(url)
    articles = []

    for entry in feed.entries:
        title = clean(entry.get("title", ""))
        link = entry.get("link", "")

        if not title or not link:
            continue

        content = entry.get("summary", "")
        if entry.get("content"):
            content = entry["content"][0].get("value", content)

        articles.append({
            "source": source,
            "title": title,
            "link": link,
            "date": get_date(entry),
            "excerpt": clean(content)[:8000],
        })

    articles.sort(
        key=lambda a: a["date"] or datetime.min.replace(tzinfo=IST),
        reverse=True,
    )
    return articles[:5]


def summarize(article):
    prompt = f"""
Summarize this news article in approximately 75 words.
Use simple, understandable English.
Explain the main development, key facts, and why it matters.
Do not invent facts. If the excerpt lacks details, acknowledge that.

Publisher: {article['source']}
Headline: {article['title']}
RSS excerpt: {article['excerpt']}
Article link: {article['link']}

Return only the summary.
"""

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an accurate and careful news editor."
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 180,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def send_telegram(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    # Keep each message safely below Telegram's message limit.
    chunks = []
    while len(text) > 3800:
        split_at = text.rfind("\n", 0, 3800)
        if split_at < 1:
            split_at = 3800
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")

    if text:
        chunks.append(text)

    for chunk in chunks:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise RuntimeError("Telegram delivery failed.")
        time.sleep(0.5)


def generate_digest():
    sections = [
        "🗞️ DAILY NEWS DIGEST",
        f"📅 {datetime.now(IST).strftime('%d %B %Y')} | 9 AM IST",
        "AI/ML • Technology • Business • Finance • Startups",
    ]
    total = 0

    for source, url in FEEDS:
        sections.extend(["", "━━━━━━━━━━━━━━━━━━", source.upper()])

        try:
            articles = fetch_articles(source, url)
        except Exception as exc:
            print(f"RSS error for {source}: {exc}")
            sections.append("Could not fetch this source today.")
            continue

        if not articles:
            sections.append("No articles available.")
            continue

        for article in articles:
            try:
                summary = summarize(article)
            except Exception as exc:
                print(f"Summary error: {exc}")
                summary = (
                    article["excerpt"][:600]
                    or "Summary unavailable. Please open the original article."
                )

            date = (
                article["date"].strftime("%d %b %Y")
                if article["date"] else "Date unavailable"
            )

            sections.extend([
                "",
                f"{total + 1}. {article['title']}",
                f"📰 {source} | {date}",
                "",
                summary,
                "",
                f"🔗 {article['link']}",
            ])
            total += 1

    sections.extend(["", "━━━━━━━━━━━━━━━━━━", f"Articles: {total}/20"])
    send_telegram("\n".join(sections))


@app.get("/")
def home():
    return {"status": "News bot is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run_news():
    secret = os.environ.get("RUN_SECRET", "")
    supplied = request.headers.get("X-Run-Secret", "")

    if not secret or not supplied or not __import__("hmac").compare_digest(
        supplied, secret
    ):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        generate_digest()
        return jsonify({"status": "News digest sent"}), 200
    except Exception:
        app.logger.exception("Digest generation failed")
        return jsonify({"error": "Digest failed; check Render logs"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)