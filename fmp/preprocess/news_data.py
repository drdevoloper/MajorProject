import yfinance as yf
import datetime
import re
import requests
import feedparser

from database.mongo import db

news_collection = db["financial_news"]


# ---------------------------------------
# CLEAN TEXT
# ---------------------------------------

def clean_text(text):

    if not text:
        return ""

    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)

    return text.strip()


# ---------------------------------------
# FETCH YAHOO FINANCE NEWS
# ---------------------------------------

def fetch_yahoo_news(symbol):

    news_list = []

    try:

        ticker = yf.Ticker(symbol)

        news = ticker.news

        if news is None or len(news) == 0:
            print(f"⚠ No Yahoo news for {symbol}")
            return []

        for item in news:

            title = clean_text(item.get("title", ""))

            if title == "":
                continue

            news_list.append({

                "symbol": symbol,
                "title": title,
                "publisher": item.get("publisher", "Yahoo"),
                "link": item.get("link", ""),

                "source": "Yahoo Finance",

                "published": datetime.datetime.fromtimestamp(
                    item.get("providerPublishTime", 0)
                ),

                "fetched_at": datetime.datetime.utcnow()

            })

    except Exception as e:

        print(f"❌ Yahoo news error {symbol}: {e}")

    return news_list


# ---------------------------------------
# FETCH GOOGLE NEWS
# ---------------------------------------

def fetch_google_news(symbol):

    news_list = []

    try:

        url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"

        feed = feedparser.parse(url)

        for entry in feed.entries:

            title = clean_text(entry.title)

            if title == "":
                continue

            news_list.append({

                "symbol": symbol,
                "title": title,
                "publisher": entry.source.title if "source" in entry else "Google News",
                "link": entry.link,

                "source": "Google News",

                "published": datetime.datetime(*entry.published_parsed[:6]),

                "fetched_at": datetime.datetime.utcnow()

            })

    except Exception as e:

        print(f"❌ Google news error {symbol}: {e}")

    return news_list


# ---------------------------------------
# FETCH ALL NEWS
# ---------------------------------------

def fetch_news(symbol):

    yahoo_news = fetch_yahoo_news(symbol)

    google_news = fetch_google_news(symbol)

    all_news = yahoo_news + google_news

    return all_news


# ---------------------------------------
# STORE NEWS
# ---------------------------------------

def store_news(symbol):

    news = fetch_news(symbol)

    if not news:
        print(f"📰 0 news stored for {symbol}")
        return

    inserted = 0

    for article in news:

        exists = news_collection.find_one({

            "symbol": symbol,
            "title": article["title"]

        })

        if exists:
            continue

        news_collection.insert_one(article)

        inserted += 1

    print(f"📰 {inserted} news stored for {symbol}")


# ---------------------------------------
# GET NEWS
# ---------------------------------------

def get_news(symbol, limit=50):

    news = list(

        news_collection
        .find({"symbol": symbol})
        .sort("published", -1)
        .limit(limit)

    )

    return news