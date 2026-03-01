import yfinance as yf
import feedparser
import datetime
import re

from database.mongo import db

news_collection = db["news"]


# ===============================================
# 🔹 TEXT CLEANING
# ===============================================

def clean_text(text):
    text = re.sub(r"http\S+", "", text)      # remove urls
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)  # remove special chars
    return text.strip()


# ===============================================
# 🔹 STORE NEWS IN MONGODB
# ===============================================

def store_news(symbol, news_items):

    # Remove old news for symbol
    news_collection.delete_many({"symbol": symbol})

    if news_items:
        news_collection.insert_many(news_items)


# ===============================================
# 🔹 FETCH NEWS
# ===============================================

def get_news(symbol, limit=5):

    news_list = []
    seen_titles = set()

    # -------------------------------------------
    # 1️⃣ Primary: yfinance
    # -------------------------------------------
    try:
        ticker = yf.Ticker(symbol)
        yf_news = ticker.news

        if yf_news:
            for item in yf_news[:limit]:

                title = clean_text(item.get("title", ""))

                if title and title not in seen_titles:
                    seen_titles.add(title)

                    news_list.append({
                        "symbol": symbol,
                        "title": title,
                        "published": datetime.datetime.fromtimestamp(
                            item.get("providerPublishTime", 0)
                        ),
                        "source": "yfinance",
                        "fetched_at": datetime.datetime.utcnow()
                    })

    except Exception:
        pass

    # -------------------------------------------
    # 2️⃣ Fallback: Yahoo RSS
    # -------------------------------------------
    if len(news_list) < limit:
        try:
            rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:limit]:

                title = clean_text(entry.title)

                if title and title not in seen_titles:
                    seen_titles.add(title)

                    news_list.append({
                        "symbol": symbol,
                        "title": title,
                        "published": datetime.datetime.utcnow(),
                        "source": "yahoo_rss",
                        "fetched_at": datetime.datetime.utcnow()
                    })

        except Exception:
            pass

    # -------------------------------------------
    # Store in MongoDB
    # -------------------------------------------
    store_news(symbol, news_list)

    return news_list