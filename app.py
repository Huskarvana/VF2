import streamlit as st
import requests
import pandas as pd
import feedparser
from datetime import datetime
from transformers import pipeline

# Configuration
st.set_page_config(page_title="Agent de Veille DS Automobiles", layout="wide")
st.title("🚗 Agent de Veille DS Automobiles (multi-langues)")

# API KEYS
API_KEY_NEWSDATA = st.secrets["API_KEY_NEWSDATA"]
MEDIASTACK_API_KEY = st.secrets["MEDIASTACK_API_KEY"]
NEWSAPI_KEY = st.secrets["NEWSAPI_KEY"]

# Flux RSS EN/FR/ES
RSS_FEEDS = [
    "https://www.leblogauto.com/feed",  # FR
    "https://www.motor1.com/rss/news/",  # EN
    "https://electrek.co/feed/",  # EN
    "https://es.motor1.com/rss/noticias/"  # ES
]

MODELES_DS = ["DS N4", "DS N8", "DS7", "DS3", "DS9", "DS4", "Jules Verne", "N°8", "N°4"]

@st.cache_resource
def get_sentiment_pipeline():
    return pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")

sentiment_analyzer = get_sentiment_pipeline()

def fetch_rss_articles(query, lang):
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                titre = entry.get("title", "")
                if query.lower() in titre.lower():
                    articles.append({
                        "date": entry.get("published", "")[:10],
                        "titre": titre,
                        "contenu": entry.get("summary", "")[:512],
                        "source": feed_url,
                        "lien": entry.get("link", ""),
                        "langue": lang
                    })
        except:
            continue
    return articles

def detecter_modele(titre):
    for m in MODELES_DS:
        if m.lower() in titre.lower():
            return m
    return "DS Global"

def analyser_article(row):
    try:
        sentiment = sentiment_analyzer(row['contenu'][:512])[0]['label']
        sentiment = {"LABEL_0": "Negative", "LABEL_1": "Neutral", "LABEL_2": "Positive"}.get(sentiment, sentiment)
    except:
        sentiment = "Neutral"
    modele = detecter_modele(row['titre'])
    résumé = row['contenu'][:200] + "..."
    return pd.Series({'résumé': résumé, 'ton': sentiment, 'modèle': modele})

# Interface
st.sidebar.title("Filtres")
langues_dispo = ["fr", "en", "es"]
langues_selection = st.sidebar.multiselect("Langues", options=["tous"] + langues_dispo, default=["tous"])
filtre_modele = st.sidebar.selectbox("Filtrer par modèle", ["Tous"] + MODELES_DS)
nb_articles = st.sidebar.slider("Nombre d'articles max", 10, 100, 30)

if st.button("🔍 Lancer la veille"):
    st.info("Collecte des articles en cours...")
    all_articles = []
    for lang in langues_dispo:
        if "tous" in langues_selection or lang in langues_selection:
            all_articles += fetch_rss_articles("DS", lang)
            all_articles += fetch_rss_articles("DS Automobiles", lang)

    df = pd.DataFrame(all_articles)
    if not df.empty:
        with st.spinner("Analyse en cours..."):
            df[['résumé', 'ton', 'modèle']] = df.apply(analyser_article, axis=1)

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.sort_values(by='date', ascending=False)

        if filtre_modele != "Tous":
            df = df[df['modèle'] == filtre_modele]

        if "tous" not in langues_selection:
            df = df[df['langue'].isin(langues_selection)]

        st.dataframe(df[['date', 'titre', 'modèle', 'ton', 'résumé', 'langue', 'lien']])
    else:
        st.warning("Aucun article trouvé.")