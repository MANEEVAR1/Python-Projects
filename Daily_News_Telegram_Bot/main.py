import os
import re
import html
import hmac
import time
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

IST = ZoneInfo("Asia/Kolkata")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

GROQ_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

TELEGRAM_URL = (
    "https://api.telegram.org/bot{}/sendMessage"
)

MAX_ARTICLES = 20
ARTICLES_PER_FEED = 10
MESSAGE_LIMIT = 3500

# --------------------------------------------------
# SPECIALIZED RSS FEEDS
# --------------------------------------------------

FEEDS = [
    (
        "OpenAI",
        "https://openai.com/news/rss.xml"
    ),
    (
        "Google DeepMind",
        "https://deepmind.google/blog/rss.xml"
    ),
    (
        "Google Research",
        "https://research.google/blog/rss/"
    ),
    (
        "Hugging Face",
        "https://huggingface.co/blog/feed.xml"
    ),
    (
        "TechCrunch AI",
        "https://techcrunch.com/category/artificial-intelligence/feed/"
    ),
    (
        "TechCrunch Startups",
        "https://techcrunch.com/category/startups/feed/"
    ),
    (
        "The Verge AI",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
    ),
    (
        "WIRED AI",
        "https://www.wired.com/feed/tag/ai/latest/rss"
    ),
    (
        "Ars Technica AI",
        "https://arstechnica.com/ai/feed/"
    ),
    (
        "NVIDIA",
        "https://blogs.nvidia.com/feed/"
    ),
    (
        "arXiv AI Research",
        "https://rss.arxiv.org/rss/cs.AI"
    ),
    (
        "arXiv Machine Learning",
        "https://rss.arxiv.org/rss/cs.LG"
    ),
    (
        "arXiv Language Technology",
        "https://rss.arxiv.org/rss/cs.CL"
    ),
    (
        "arXiv Cybersecurity",
        "https://rss.arxiv.org/rss/cs.CR"
    ),
    (
        "Simon Willison",
        "https://simonwillison.net/atom/everything/"
    ),
]


# --------------------------------------------------
# RELEVANCE KEYWORDS
# --------------------------------------------------

# Strong matches receive higher scores.
HIGH_PRIORITY = [
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "large language model",
    "small language model",
    "frontier model",
    "reasoning model",
    "openai",
    "anthropic",
    "google deepmind",
    "meta ai",
    "xai",
    "deepseek",
    "mistral ai",
    "llama model",
    "gemini model",
    "claude model",
    "gpt-",
    "llm",
    "slm",
    "ai agent",
    "agentic ai",
    "generative ai",
    "computer science",
    "programming language",
    "software engineering",
    "open source",
    "cybersecurity",
    "zero-day",
    "zero day",
    "data breach",
    "security vulnerability",
    "ransomware",
    "startup funding",
    "venture capital",
    "ai startup",
    "elon musk",
    "tesla",
    "spacex",
    "robotics",
    "semiconductor",
    "gpu",
    "inference",
    "model training",
    "ai benchmark",
    "ai research",
    "neural network",
    "transformer model",
    "computer vision",
    "reinforcement learning",
    "model release",
    "ai chip",
]

MEDIUM_PRIORITY = [
    "technology",
    "developer",
    "developers",
    "github",
    "python",
    "javascript",
    "typescript",
    "rust programming",
    "database",
    "cloud computing",
    "distributed systems",
    "operating system",
    "algorithm",
    "api",
    "framework",
    "inference engine",
    "fine-tuning",
    "fine tuning",
    "quantization",
    "synthetic data",
    "training data",
    "model weights",
    "benchmark",
    "research paper",
    "cyber attack",
    "cyberattack",
    "encryption",
    "malware",
    "hacker",
    "security patch",
    "funding round",
    "acquisition",
    "venture funding",
    "product launch",
    "technology company",
    "data center",
    "semiconductors",
    "autonomous driving",
    "humanoid robot",
    "ai safety",
    "model evaluation",
    "machine reasoning",
    "infrastructure",
    "cloud infrastructure",
    "developer tools",
]

# These topics are allowed only when connected
# to a relevant technology or business development.
CONTEXT_TERMS = [
    "business",
    "finance",
    "investment",
    "funding",
    "revenue",
    "valuation",
    "earnings",
    "acquisition",
    "market",
    "product",
    "launch",
    "company",
    "startup",
    "founder",
    "research",
    "security",
]


# --------------------------------------------------
# TEXT UTILITIES
# --------------------------------------------------

def clean_text(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title):
    title = clean_text(title).lower()
    title = re.sub(r"[^a-z0-9]+", " ", title)
    return title.strip()


def escape_html(text):
    return html.escape(str(text or ""), quote=True)


# --------------------------------------------------
# ARTICLE DATE
# --------------------------------------------------

def get_article_date(entry):
    for key in ("published", "updated"):
        try:
            date = parsedate_to_datetime(entry[key])

            if date.tzinfo is None:
                date = date.replace(
                    tzinfo=ZoneInfo("UTC")
                )

            return date.astimezone(IST)

        except (KeyError, ValueError, TypeError):
            continue

    return None


# --------------------------------------------------
# RELEVANCE SCORING
# --------------------------------------------------

def score_article(article):
    title = article["title"].lower()
    content = article["excerpt"].lower()

    score = 0

    for keyword in HIGH_PRIORITY:
        if keyword in title:
            score += 5

        elif keyword in content:
            score += 2

    for keyword in MEDIUM_PRIORITY:
        if keyword in title:
            score += 3

        elif keyword in content:
            score += 1

    # Give a small boost to recent stories.
    published = article.get("date")

    if published:
        age_hours = (
            datetime.now(IST) - published
        ).total_seconds() / 3600

        if 0 <= age_hours <= 24:
            score += 3

        elif 24 < age_hours <= 72:
            score += 2

        elif 72 < age_hours <= 168:
            score += 1

    # Avoid unrelated business or finance stories.
    broad_business_terms = [
        "stock market",
        "share price",
        "quarterly earnings",
        "cryptocurrency price",
        "bitcoin price",
    ]

    is_broad_finance = any(
        term in title for term in broad_business_terms
    )

    has_tech_context = any(
        term in title or term in content
        for term in HIGH_PRIORITY[:]
        if term not in {
            "business",
            "finance",
            "investment",
        }
    )

    if is_broad_finance and not has_tech_context:
        score -= 10

    return score


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

    if feed.bozo and not feed.entries:
        raise ValueError("Invalid RSS feed")

    articles = []

    for entry in feed.entries:
        title = clean_text(
            entry.get("title", "")
        )

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
            "excerpt": clean_text(content)[:8000],
        }

        article["score"] = score_article(article)

        # Reject weakly relevant articles.
        if article["score"] >= 3:
            articles.append(article)

    articles.sort(
        key=lambda item: (
            item["score"],
            item["date"] or datetime.min.replace(
                tzinfo=IST
            ),
        ),
        reverse=True,
    )

    return articles[:ARTICLES_PER_FEED]


# --------------------------------------------------
# SELECT RELEVANT STORIES
# --------------------------------------------------

def select_top_articles():
    candidates = []

    for source, feed_url in FEEDS:
        try:
            articles = fetch_articles(
                source,
                feed_url
            )

            candidates.extend(articles)

            app.logger.info(
                "%s: %s relevant candidates",
                source,
                len(articles),
            )

        except Exception:
            app.logger.exception(
                "Could not fetch feed: %s",
                source,
            )

    # Remove duplicate titles across feeds.
    unique_articles = []
    seen_titles = set()

    for article in sorted(
        candidates,
        key=lambda item: item["score"],
        reverse=True,
    ):
        normalized = normalize_title(
            article["title"]
        )

        if normalized in seen_titles:
            continue

        seen_titles.add(normalized)
        unique_articles.append(article)

    # Select the 20 strongest matches overall.
    unique_articles.sort(
        key=lambda item: (
            item["score"],
            item["date"] or datetime.min.replace(
                tzinfo=IST
            ),
        ),
        reverse=True,
    )

    selected = unique_articles[:MAX_ARTICLES]

    app.logger.info(
        "Selected %s unique stories",
        len(selected),
    )

    return selected


# --------------------------------------------------
# GROQ SUMMARY GENERATION
# --------------------------------------------------

def summarize_article(article):
    prompt = f"""
Write a useful news summary of approximately
75 words in simple, clear English.

Explain:
- What happened?
- What are the key facts?
- Why does it matter?

Rules:
- Write one connected paragraph.
- Aim for 70-85 words.
- Do not repeat the headline.
- Do not include links.
- Do not use bullet points.
- Never invent facts.
- Distinguish claims from confirmed facts.
- Use only the information provided.
- If the excerpt is insufficient, explain the
  limitation instead of guessing.

Headline: {article['title']}
Publisher: {article['source']}
Available article text: {article['excerpt']}

Return only the summary paragraph.
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
                        "You are an accurate technology "
                        "and business news editor. "
                        "Never fabricate facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
            "max_completion_tokens": 1200,
            "reasoning_effort": "low",
        },
        timeout=90,
    )

    if not response.ok:
        app.logger.error(
            "Groq API error %s: %s",
            response.status_code,
            response.text[:1500],
        )

        response.raise_for_status()

    data = response.json()

    choices = data.get("choices", [])

    if not choices:
        raise ValueError(
            "Groq returned no choices"
        )

    summary = (
        choices[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    if not summary:
        raise ValueError(
            "Groq returned an empty summary"
        )

    return summary


# --------------------------------------------------
# FORMAT STORIES
# --------------------------------------------------

def format_story(article, number):
    title = escape_html(article["title"])

    try:
        summary = summarize_article(article)

    except Exception:
        app.logger.exception(
            "Summary failed: %s",
            article["title"],
        )

        summary = (
            "Summary unavailable because the AI service "
            "could not process this story. Please try again."
        )

    summary = escape_html(summary)

    return (
        f"<b>Story {number} – {title}</b>\n\n"
        f"{summary}"
    )


# --------------------------------------------------
# SPLIT TELEGRAM MESSAGES
# --------------------------------------------------

def split_messages(text, limit=MESSAGE_LIMIT):
    messages = []
    current = ""

    for paragraph in text.split("\n"):
        candidate = (
            current + "\n" + paragraph
            if current
            else paragraph
        )

        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            messages.append(current)
            current = ""

        while len(paragraph) > limit:
            messages.append(paragraph[:limit])
            paragraph = paragraph[limit:]

        current = paragraph

    if current:
        messages.append(current)

    return messages


# --------------------------------------------------
# SEND TELEGRAM DIGEST
# --------------------------------------------------

def send_telegram(text):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = TELEGRAM_URL.format(token)

    for message in split_messages(text):
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
                "Telegram delivery failed"
            )

        time.sleep(0.5)


# --------------------------------------------------
# GENERATE DAILY DIGEST
# --------------------------------------------------

def generate_digest():
    today = datetime.now(IST).strftime(
        "%d %B %Y"
    )

    articles = select_top_articles()

    sections = [
        "<b>🗞️ DAILY AI & TECH DIGEST</b>",
        f"📅 {today}",
        (
            "AI/ML • LLMs/SLMs • Programming • "
            "Cybersecurity • Startups • Tech Business"
        ),
        "━━━━━━━━━━━━━━━━━━",
    ]

    current_source = None

    for number, article in enumerate(
        articles,
        start=1,
    ):
        source = article["source"]

        if source != current_source:
            sections.extend([
                "",
                f"📌 <b>{escape_html(source.upper())}</b>",
                "",
            ])

            current_source = source

        story = format_story(
            article,
            number,
        )

        sections.extend([
            story,
            "",
            "──────────────────",
            "",
        ])

    sections.extend([
        "",
        f"<b>Total Stories: {len(articles)}</b>",
        "End of Daily Digest.",
    ])

    digest = "\n".join(sections)

    send_telegram(digest)

    app.logger.info(
        "Digest sent: %s stories",
        len(articles),
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
# SCHEDULED EXECUTION ENDPOINT
# --------------------------------------------------

@app.post("/run")
def run_news():
    secret = os.environ.get("RUN_SECRET", "")
    supplied = request.headers.get(
        "X-Run-Secret",
        "",
    )

    if (
        not secret
        or not supplied
        or not hmac.compare_digest(
            secret,
            supplied,
        )
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
            "Digest generation failed"
        )

        return jsonify({
            "error": (
                "Digest failed. Check Render logs."
            )
        }), 500


# --------------------------------------------------
# START APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )