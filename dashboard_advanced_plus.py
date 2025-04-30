
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import requests
from bs4 import BeautifulSoup
import time

# 🔐 Connessione al database (usando secrets)
DB_URL = st.secrets["connection_string"]
engine = create_engine(DB_URL)

# Configura layout con sidebar a destra
st.set_page_config(page_title="TGC Tours Dashboard", layout="wide")

# Custom CSS per sidebar a destra e stile tabella
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            float: right;
        }
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
        .dataframe tbody tr th {
            vertical-align: top;
        }
        .dataframe thead th {
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# 📊 Caricamento dati
@st.cache_data
def load_data():
    query = """
    SELECT l.*, t.week, t.dates, t.tournament_name, t.course, t.purse
    FROM leaderboards l
    JOIN tournaments t ON l.tournament_id = t.id
    """
    return pd.read_sql(query, engine)

df = load_data()

# 🎛️ Filtro gruppo
group_options = ["Tutti"] + sorted(df["group"].unique())
selected_group = st.sidebar.selectbox("Filtro gruppo", group_options)
if selected_group != "Tutti":
    df = df[df["group"] == selected_group]

# 🎛️ Filtro torneo combinato
df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " - " + df["tournament_name"] + " (" + df["dates"] + ")"
tornei_unici = sorted(df["torneo_label"].unique())
selected_tournament = st.sidebar.selectbox("Filtro torneo", tornei_unici)
df = df[df["torneo_label"] == selected_tournament]

# ➕ Calcolo posizione in base ai colpi
df["posizione"] = df.groupby("torneo_label")["strokes"].rank(method="min").astype(int)

# 📋 Mostra tabella risultati (con colonne selezionate)
st.title("Risultati torneo selezionato")

# Ordina per posizione
df = df.sort_values(by="posizione")

# Colonne da mostrare
columns_to_show = [
    "posizione", "player", "group", "nationality", "platform",
    "r1", "r2", "r3", "r4", "strokes", "total", "earnings", "promotion",
    "tournament_name", "course", "purse", "dates"
]

# Mostra tabella finale
st.dataframe(df[columns_to_show].reset_index(drop=True))
