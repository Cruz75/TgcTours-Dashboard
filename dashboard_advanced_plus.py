import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from streamlit_calendar import calendar

# ---- Configurazione pagina ----
st.set_page_config(page_title="TGC Tours Dashboard 2025", layout="wide")
st.title("🏌️‍♂️ TGC Tours Dashboard 2025")
st.markdown("Analisi completa dei tornei PGA Tour 2K25: filtra, esplora e aggiorna i dati con un click.")
st.markdown("---")

# ---- Connessione a Supabase ----
DB_URL = st.secrets["connection_string"]
engine = create_engine(DB_URL)

# ---- Caricamento dati ----
@st.cache_data(ttl=600)
def load_data():
    query = """
    SELECT l.*, t.week, t.dates, t.tournament_name, t.course, t.purse
    FROM leaderboards AS l
    JOIN tournaments AS t ON l.tournament_id = t.id
    """
    return pd.read_sql(query, engine)

df = load_data()

# ---- Estrai date torneo ----
def estrai_date_range(date_str):
    try:
        start, end = date_str.split(" - ")
        start = pd.to_datetime(start, format="%m/%d")
        end = pd.to_datetime(end, format="%m/%d")
        return start.replace(year=2025), end.replace(year=2025)
    except:
        return pd.NaT, pd.NaT

df["start_date"], df["end_date"] = zip(*df["dates"].apply(estrai_date_range))

# ---- Funzione di aggiornamento dei tornei ----
def update_all():
    import scraper_update_fixed
    scraper_update_fixed.main()

if st.button("🔄 Aggiorna database tornei"):
    with st.spinner("Aggiornamento in corso..."):
        try:
            update_all()
            st.success("✅ Database tornei aggiornato")
        except Exception as e:
            st.error(f"Errore: {e}")
st.markdown("---")

# ---- Sidebar filtri ----
st.sidebar.header("Filtri")
# Placeholder per selezione torneo visualizzata in alto
placeholder = st.sidebar.empty()

group_options = ["Tutti"] + sorted(df["group"].unique())
selected_group = st.sidebar.selectbox("Gruppo", group_options)
if selected_group != "Tutti":
    df = df[df["group"] == selected_group]

platform_options = ["Tutti"] + sorted(df["platform"].dropna().unique())
selected_platform = st.sidebar.selectbox("Piattaforma", platform_options)
if selected_platform != "Tutti":
    df = df[df["platform"] == selected_platform]

nation_options = ["Tutti"] + sorted(df["nationality"].dropna().unique())
selected_nation = st.sidebar.selectbox("Nazionalità", nation_options)
if selected_nation != "Tutti":
    df = df[df["nationality"] == selected_nation]

# ---- Selezione torneo ----
df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " – " + df["tournament_name"] + " (" + df["dates"] + ")"
tornei_unici = sorted(df["torneo_label"].unique())
selected_tournament = st.sidebar.radio("Torneo", tornei_unici)
# Aggiorna placeholder sopra
placeholder.markdown(f"**Selezionato:** {selected_tournament}")

df = df[df["torneo_label"] == selected_tournament]


# ---- Calcolo posizione e format valori ----
df["completo"] = df[["r1","r2","r3","r4"]].notnull().all(axis=1)
completi = df[df["completo"]].copy()
completi["posizione"] = completi["strokes"].rank(method="min").astype(int)
incompleti = df[~df["completo"]].copy()
incompleti["posizione"] = None
df = pd.concat([completi, incompleti]).sort_values(by=["completo","posizione"], ascending=[False,True])

df["earnings"] = df["earnings"].apply(lambda x: f"${x:,}" if pd.notnull(x) and x else "")
df["purse"] = df["purse"].apply(lambda x: f"${x:,}" if pd.notnull(x) else "")
def promo_icons(promo):
    if not promo or pd.isna(promo): return ""
    mapping = {"+1":"🟢", "-1":"🔴", "winner":"🏆", "fast_track":"⚡"}
    return " ".join(mapping.get(m, "") for m in promo.split(","))
df["promotion"] = df["promotion"].apply(promo_icons)

# ---- Tabella risultati ----
st.subheader("Classifica Torneo")
columns = ["posizione","player","group","nationality","platform",
           "r1","r2","r3","r4","strokes","total","earnings","promotion",
           "tournament_name","course","purse","dates"]
st.dataframe(df[columns], height=600, use_container_width=True)

