import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from langdetect import detect
from transformers import pipeline

# Configuration
st.set_page_config(page_title="Veille DS Automobiles", layout="wide")
st.title("🔎 Agent de veille – DS Automobiles")

API_KEY_NEWSDATA = st.secrets["API_KEY_NEWSDATA"]

@st.cache_resource
def get_sentiment_pipeline():
    return pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
sentiment_analyzer = get_sentiment_pipeline()

def detect_lang(text):
    try:
        return detect(text)
    except:
        return "unknown"

def fetch_newsdata_articles(query, lang, max_results=30):
    url = "https://newsdata.io/api/1/news"
    country_map = {"en": "us", "fr": "fr", "es": "es"}
    params = {
        "apikey": API_KEY_NEWSDATA,
        "q": query,
        "language": lang,
        "country": country_map.get(lang, ""),
        "page": 1
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return [{
            "date": item.get("pubDate", ""),
            "titre": item.get("title", ""),
            "contenu": item.get("description", "") or "",
            "source": item.get("source_id", ""),
            "lien": item.get("link", "")
        } for item in data.get("results", [])[:max_results]]
    except Exception as e:
        st.error(f"Erreur API NewsData pour langue '{lang}': {e}")
        return []

def analyser_article(row):
    try:
        ton = sentiment_analyzer(row["contenu"][:512])[0]["label"]
    except:
        ton = "neutral"
    try:
        langue = detect_lang(row["contenu"])
    except:
        langue = "unknown"
    résumé = row["contenu"][:200] + "..."
    return pd.Series({"résumé": résumé, "ton": ton.upper(), "langue": langue})

st.sidebar.header("🎛️ Filtres")
langue_select = st.sidebar.multiselect("Langues", ["fr", "en", "es"], default=["fr"])
nb_articles = st.sidebar.slider("Nombre d'articles à récupérer", 10, 100, 30)

if st.button("🔍 Lancer la veille maintenant"):
    with st.spinner("Chargement..."):
        all_articles = []
        for lang in langue_select:
            all_articles.extend(fetch_newsdata_articles("DS Automobiles", lang, max_results=nb_articles))

        articles = pd.DataFrame(all_articles)

        if not articles.empty:
            articles[["résumé", "ton", "langue"]] = articles.apply(analyser_article, axis=1)
            articles["date"] = pd.to_datetime(articles["date"], errors="coerce")
            articles = articles.dropna(subset=["date"])
            articles = articles.sort_values(by="date", ascending=False)
            st.success(f"{len(articles)} article(s) trouvés.")
            st.dataframe(articles[["date", "titre", "ton", "langue", "résumé", "source", "lien"]])
        else:
            st.warning("Aucun article trouvé pour les langues sélectionnées.")
