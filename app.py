
import streamlit as st
import requests
import pandas as pd
import feedparser
from newsapi import NewsApiClient
from datetime import datetime
from dateutil import parser as dateparser

st.set_page_config(page_title="Agent DS - Multilingue", layout="wide")
st.title("📰 Agent de Veille – DS Automobiles")

# Clés API
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "")

# RSS anglophones
RSS_FEEDS_EN = [
    "https://www.insideevs.com/rss/news/all/",
    "https://www.motor1.com/news/rss/",
    "https://electrek.co/feed/",
    "https://en.wikinews.org/wiki/Main_Page?feed=atom",
    "https://www.autocar.co.uk/rss.xml",
    "https://www.carscoops.com/feed/",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Automobiles.xml"
]

# Collecte depuis RSS
def fetch_rss_articles(rss_list, lang="en"):
    articles = []
    for url in rss_list:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            titre = entry.title
            lien = entry.link
            date_pub = entry.get("published", "") or entry.get("updated", "")
            try:
                date = dateparser.parse(date_pub)
            except:
                date = None
            articles.append({
                "titre": titre,
                "lien": lien,
                "date": date,
                "langue": lang,
                "source": url
            })
    return articles

# Collecte depuis NewsAPI
def fetch_newsapi_articles(query="DS Automobiles", lang="en", limit=20):
    if not NEWSAPI_KEY:
        return []
    api = NewsApiClient(api_key=NEWSAPI_KEY)
    try:
        res = api.get_everything(q=query, language=lang, sort_by='publishedAt', page_size=limit)
        return [{
            "titre": a["title"],
            "lien": a["url"],
            "date": dateparser.parse(a["publishedAt"]),
            "langue": lang,
            "source": "NewsAPI"
        } for a in res["articles"]]
    except Exception as e:
        return []

# Interface utilisateur
langue = st.selectbox("Filtrer par langue", ["Tous", "fr", "en", "es"])
keyword = st.text_input("🔍 Recherche par mot-clé (optionnel)", "")

if st.button("🔍 Lancer la veille"):
    articles = []

    if langue in ["Tous", "en"]:
        articles += fetch_rss_articles(RSS_FEEDS_EN, lang="en")
        articles += fetch_newsapi_articles(query=keyword or "DS Automobiles", lang="en")

    df = pd.DataFrame(articles)
    if not df.empty:
        df = df.drop_duplicates(subset="titre")
        df['date'] = pd.to_datetime(df['date'], errors="coerce")
        df = df.sort_values(by="date", ascending=False)
        st.dataframe(df[['date', 'titre', 'lien', 'langue', 'source']])
    else:
        st.warning("Aucun article trouvé.")
