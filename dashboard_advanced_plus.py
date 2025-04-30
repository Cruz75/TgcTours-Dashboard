
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import requests
from bs4 import BeautifulSoup
import time

# 🔐 Connessione al database (usando secrets)
DB_URL = st.secrets["connection_string"]
engine = create_engine(DB_URL)

# Configura layout con sidebar a destra
st.set_page_config(page_title="TGC Tours Dashboard", layout="wide")

# Custom CSS
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

# 🔄 Funzione di aggiornamento solo promotion
def update_promotions():
    query = "SELECT DISTINCT tournament_id FROM leaderboards"
    existing_ids = pd.read_sql(query, engine)['tournament_id'].tolist()

    updated = 0
    for tid in existing_ids:
        url = f"https://www.tgctours.com/Tournament/Leaderboard/{tid}?showEarnings=True"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 12:
                try:
                    player_tag = cols[2].find("a")
                    player_name = player_tag.text.strip()

                    marks_cell = cols[11]
                    icons = marks_cell.find_all("i")
                    marks = []
                    for icon in icons:
                        cls = icon.get("class", [])
                        if "fe-icon-arrow-up-circle" in cls:
                            marks.append("+1")
                        elif "fe-icon-arrow-down-circle" in cls:
                            marks.append("-1")
                        elif "fe-icon-award" in cls:
                            marks.append("winner")
                        elif "fa" in cls and "fa-bolt" in cls:
                            marks.append("fast_track")
                    promotion_str = ",".join(marks)

                    if promotion_str:
                        with engine.begin() as conn:
                            conn.execute(text("""
                                UPDATE leaderboards
                                SET promotion = :promotion
                                WHERE player = :player AND tournament_id = :tid
                            """), {"promotion": promotion_str, "player": player_name, "tid": tid})
                        updated += 1
                except:
                    continue
        time.sleep(0.3)
    return updated

# 🔘 Bottone per aggiornare promozioni
if st.button("🔄 Aggiorna promozioni mancanti"):
    with st.spinner("Controllo e aggiornamento promozioni..."):
        count = update_promotions()
        st.success(f"✅ {count} promozioni aggiornate!")

df = load_data()

# 🎛️ Filtro gruppo
group_options = ["Tutti"] + sorted(df["group"].unique())
selected_group = st.sidebar.selectbox("Filtro gruppo", group_options)
if selected_group != "Tutti":
    df = df[df["group"] == selected_group]

# 🎛️ Filtro torneo combinato
df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " - " + df["tournament_name"] + " (" + df["dates"] + ")"
tornei_unici = sorted(df["torneo_label"].unique())
selected_tournament = st.sidebar.radio("Seleziona torneo", tornei_unici)
df = df[df["torneo_label"] == selected_tournament]

# ➕ Calcolo posizione (solo se ha tutti i round completati)
df["completo"] = df[["r1", "r2", "r3", "r4"]].notnull().all(axis=1)

df["posizione"] = None
completi = df[df["completo"]].copy()
completi["posizione"] = completi["strokes"].rank(method="min").astype(int)
incompleti = df[~df["completo"]].copy()
incompleti["posizione"] = None

df = pd.concat([completi, incompleti])
df = df.sort_values(by=["completo", "posizione"], ascending=[False, True])

# 💲 Format money + fix promotion
df["earnings"] = df["earnings"].apply(lambda x: f"${x:,}" if pd.notnull(x) and x != "" else "")
df["purse"] = df["purse"].apply(lambda x: f"${x:,}" if pd.notnull(x) else "")
df["promotion"] = df["promotion"].fillna("")

# 📋 Mostra tabella risultati
st.title("Risultati torneo selezionato")
columns_to_show = [
    "posizione", "player", "group", "nationality", "platform",
    "r1", "r2", "r3", "r4", "strokes", "total", "earnings", "promotion",
    "tournament_name", "course", "purse", "dates"
]
st.dataframe(df[columns_to_show].reset_index(drop=True))
