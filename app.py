
import streamlit as st
import requests
import pandas as pd
import feedparser
from newsapi import NewsApiClient
from datetime import datetime
from dateutil import parser as dateparser

st.set_page_config(page_title="Agent DS - Multilingue", layout="wide")
st.title("📰 Agent de Veille – DS Automobiles")

NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "")

MODELES_DS = ["DS3", "DS4", "DS7", "DS9", "DS N4", "DS N8", "Jules Verne", "N°4", "N°8"]

RSS_FEEDS = {
    "fr": [
        "https://news.google.com/rss/search?q=DS+Automobiles&hl=fr&gl=FR&ceid=FR:fr",
        "https://www.leblogauto.com/feed"
    ],
    "en": [
        "https://www.insideevs.com/rss/news/all/",
        "https://www.motor1.com/news/rss/",
        "https://electrek.co/feed/",
        "https://en.wikinews.org/wiki/Main_Page?feed=atom",
        "https://www.autocar.co.uk/rss.xml",
        "https://www.carscoops.com/feed/",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Automobiles.xml"
    ]
}

NEWSAPI_LANGUAGES = ["fr", "en", "es"]

def detect_model(text):
    for model in MODELES_DS:
        if model.lower() in text.lower():
            return model
    return "DS Global"

def fetch_rss_articles(rss_list, lang):
    articles = []
    for url in rss_list:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            titre = entry.title
            lien = entry.link
            if "ds" not in titre.lower():
                continue
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
                "source": url,
                "modèle": detect_model(titre)
            })
    return articles

def fetch_newsapi_articles(lang, limit=50):
    if not NEWSAPI_KEY or lang not in NEWSAPI_LANGUAGES:
        return []
    api = NewsApiClient(api_key=NEWSAPI_KEY)
    try:
        res = api.get_everything(q="DS Automobiles", language=lang, sort_by='publishedAt', page_size=min(limit, 100))
        return [{
            "titre": a["title"],
            "lien": a["url"],
            "date": dateparser.parse(a["publishedAt"]),
            "langue": lang,
            "source": "NewsAPI",
            "modèle": detect_model(a["title"])
        } for a in res["articles"] if "ds" in a["title"].lower()]
    except Exception:
        return []

langue = st.selectbox("🌍 Filtrer par langue", ["Tous", "fr", "en", "es"])
filtre_modele = st.selectbox("🚘 Filtrer par modèle", ["Tous"] + MODELES_DS)
keyword = st.text_input("🔎 Recherche par mot-clé (optionnel)", "")
max_articles = st.slider("📰 Nombre d’articles NewsAPI par langue", min_value=10, max_value=100, step=10, value=30)

if st.button("🕵️ Lancer la veille"):
    all_articles = []
    selected_langs = ["fr", "en", "es"] if langue == "Tous" else [langue]

    for lang in selected_langs:
        if lang in RSS_FEEDS:
            all_articles += fetch_rss_articles(RSS_FEEDS[lang], lang)
        all_articles += fetch_newsapi_articles(lang=lang, limit=max_articles)

    df = pd.DataFrame(all_articles)
    if not df.empty:
        df = df.drop_duplicates(subset="titre")
        df['date'] = pd.to_datetime(df['date'], errors="coerce")
        df = df.sort_values(by="date", ascending=False)

        if filtre_modele != "Tous":
            df = df[df["modèle"] == filtre_modele]

        st.dataframe(df[['date', 'titre', 'modèle', 'langue', 'lien', 'source']])
    else:
        st.warning("Aucun article trouvé.")
