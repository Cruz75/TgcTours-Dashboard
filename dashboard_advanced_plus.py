import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

# ---- Configurazione pagina ----
st.set_page_config(page_title="TGC Tours Dashboard", layout="wide")
st.title("🏌️ TGC Tours Dashboard")
st.markdown("Visualizza e aggiorna i risultati dei tornei PGA Tour 2K25.")
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

# ---- Preparazione dati ----
@st.cache_data(ttl=600)
def prepare_dataframe(df):
    df = df.copy()
    df["torneo_label"] = (
        df["week"].astype(str).str.zfill(2) + " – " + df["tournament_name"] + " (" + df["dates"] + ")"
    )
    df["completo"] = df[["r1", "r2", "r3", "r4"]].notnull().all(axis=1)

    # Promotion icons
    df["promotion"] = df["promotion"].fillna("")
    icon_map = {"+1": "🟢", "-1": "🔴", "winner": "🏆", "fast_track": "⚡"}

    def render_icons(p):
        return " ".join(icon_map.get(i, "") for i in p.split(",")) if p else ""

    df["promotion_icon"] = df["promotion"].apply(render_icons)

    # Ordinamento classifica
    df_completi = df[df["completo"]].copy()
    df_completi = df_completi.sort_values(by=["strokes", "r4", "r3", "r2", "r1"], ascending=True)
    df_completi["posizione"] = range(1, len(df_completi) + 1)

    df_incompleti = df[~df["completo"]].copy()
    df_incompleti["posizione"] = None

    df_final = pd.concat([df_completi, df_incompleti], ignore_index=True)
    return df_final

# ---- Filtri ----
@st.cache_data()
def filter_data(df, group, platform, nation, torneo):
    df = df.copy()
    if group != "Tutti":
        df = df[df["group"] == group]
    if platform != "Tutti":
        df = df[df["platform"] == platform]
    if nation != "Tutti":
        df = df[df["nationality"] == nation]
    if torneo:
        df = df[df["torneo_label"] == torneo]
    return df

# ---- Pulsante aggiornamento ----
def update_all():
    import scraper_update
    scraper_update.main()

if st.button("🔄 Aggiorna database tornei"):
    with st.spinner("Aggiornamento in corso..."):
        try:
            update_all()
            st.success("✅ Database aggiornato")
        except Exception as e:
            st.error(f"Errore: {e}")

st.markdown("---")

# ---- Workflow principale ----
df_raw = load_data()
df = prepare_dataframe(df_raw)

# Sidebar filtri
st.sidebar.header("Filtri")
groups = ["Tutti"] + sorted(df["group"].dropna().unique())
platforms = ["Tutti"] + sorted(df["platform"].dropna().unique())
nations = ["Tutti"] + sorted(df["nationality"].dropna().unique())
tornei = sorted(df["torneo_label"].unique())

sel_group = st.sidebar.selectbox("Gruppo", groups)
sel_platform = st.sidebar.selectbox("Piattaforma", platforms)
sel_nation = st.sidebar.selectbox("Nazionalità", nations)
sel_torneo = st.sidebar.radio("Torneo", tornei)

# Filtra dati
df_filtered = filter_data(df, sel_group, sel_platform, sel_nation, sel_torneo)

# ---- Classifica ----
st.subheader("Classifica Giocatori")
columns = [
    "posizione", "player", "group", "nationality", "platform",
    "r1", "r2", "r3", "r4", "strokes", "total",
    "earnings", "promotion_icon"
]
st.dataframe(df_filtered[columns], height=600, use_container_width=True)
