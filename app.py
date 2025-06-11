
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from transformers import pipeline
from langdetect import detect

# Chargement des clés secrètes
API_KEY_NEWSDATA = st.secrets["API_KEY_NEWSDATA"]
MEDIASTACK_API_KEY = st.secrets["MEDIASTACK_API_KEY"]
API_KEY_NEWSAPI = st.secrets["API_KEY_NEWSAPI"]

# Liste des modèles DS
MODELES_DS = ["DS", "DS Automobiles", "DS7", "DS9", "DS4", "DS3", "DS N4", "DS N8", "N°8", "N°4"]

# Pipelines d'analyse de sentiments
@st.cache_resource
def get_sentiment_pipeline():
    return pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")

sentiment_analyzer = get_sentiment_pipeline()

# Fonction pour détecter la langue
def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

# Fonction pour détecter le modèle DS mentionné
def detect_model(text):
    for model in MODELES_DS:
        if model.lower() in text.lower():
            return model
    return "Autre"

# Fonction d'analyse d'article
def analyser_article(article):
    text = article.get("description") or article.get("content") or ""
    model = detect_model(article.get("title", ""))
    lang = detect_language(text)
    try:
        tone = sentiment_analyzer(text[:512])[0]["label"]
    except:
        tone = "neutral"
    return pd.Series({
        "date": article.get("pubDate") or article.get("published_at") or "",
        "titre": article.get("title"),
        "contenu": text,
        "source": article.get("source_id") or article.get("source"),
        "lien": article.get("link") or article.get("url"),
        "langue": lang,
        "modèle": model,
        "ton": tone.capitalize()
    })

# Requête combinée pour NewData
def fetch_newsdata_articles():
    query = "DS Automobiles OR DS brand OR DS France"
    url = "https://newsdata.io/api/1/news"
    params = {
        "apikey": API_KEY_NEWSDATA,
        "q": query,
        "page": 1
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])
    except Exception as e:
        st.warning(f"Erreur API NewsData: {e}")
        return []

# Interface utilisateur
st.title("🔎 Agent de veille DS Automobiles")
langues_disponibles = ["Toutes", "fr", "en", "es"]
langue_choisie = st.multiselect("Langues souhaitées", options=langues_disponibles, default=["Toutes"])
nb_articles = st.slider("Nombre max d'articles", 5, 50, 20)

if st.button("Lancer l'analyse"):
    raw_articles = fetch_newsdata_articles()
    df = pd.DataFrame(raw_articles)
    if df.empty:
        st.warning("Aucun article trouvé.")
    else:
        with st.spinner("Analyse en cours..."):
            analyse = df.apply(analyser_article, axis=1)
            resultats = pd.concat([df, analyse], axis=1)
            resultats["date"] = pd.to_datetime(resultats["date"], errors="coerce")
            resultats = resultats.sort_values(by="date", ascending=False)

            # Filtrage langue
            if "Toutes" not in langue_choisie:
                resultats = resultats[resultats["langue"].isin(langue_choisie)]

            st.dataframe(resultats[["date", "titre", "modèle", "ton", "langue", "source", "lien"]].head(nb_articles))
