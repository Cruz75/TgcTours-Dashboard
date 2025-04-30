import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text

# ---- Configurazione pagina ----
st.set_page_config(page_title="TGC Tours Dashboard 2025", layout="wide")
st.title("🏌️‍♂️ TGC Tours Dashboard 2025")
st.markdown("Analisi completa dei tornei PGA Tour 2K25: filtra, esplora e aggiorna i dati con un click.")
st.markdown("---")

# ---- Connessione a Supabase ----
DB_URL = st.secrets["connection_string"]
engine = create_engine(DB_URL)

# ---- Caricamento dati raw ----
@st.cache_data(ttl=600)
def load_data():
    query = """
    SELECT l.*, t.week, t.dates, t.tournament_name, t.course, t.purse
    FROM leaderboards AS l
    JOIN tournaments AS t ON l.tournament_id = t.id
    """
    return pd.read_sql(query, engine)

# ---- Preparazione dati (ranking, formattazioni) ----
@st.cache_data(ttl=600)
def prepare_dataframe(df_raw):
    df = df_raw.copy()
    # Crea label torneo per selezione
    df["torneo_label"] = (
        df["week"].astype(str).str.zfill(2)
        + " – "
        + df["tournament_name"]
        + " ("
        + df["dates"]
        + ")"
    )
    # Calcolo posizione
    df["completo"] = df[["r1", "r2", "r3", "r4"]].notnull().all(axis=1)
    completati = df[df["completo"]].copy()
    completati["posizione"] = completati["strokes"].rank(method="min").astype(int)
    incompleti = df[~df["completo"]].copy()
    incompleti["posizione"] = None
    df = pd.concat([completati, incompleti]).sort_values(
        by=["completo", "posizione"], ascending=[False, True]
    )
    # Format valori monetari
    df["earnings"] = df["earnings"].apply(lambda x: f"${x:,}" if pd.notnull(x) and x else "")
    df["purse"] = df["purse"].apply(lambda x: f"${x:,}" if pd.notnull(x) else "")
    # Icone promozioni/retrocessioni
    def promo_icons(promo):
        if not promo or pd.isna(promo):
            return ""
        mapping = {"+1": "🟢", "-1": "🔴", "winner": "🏆", "fast_track": "⚡"}
        return " ".join(mapping.get(m, "") for m in promo.split(","))
    df["promotion"] = df["promotion"].apply(promo_icons)
    return df

# ---- Filtraggio dati ----
@st.cache_data()
def filter_dataframe(df_processed, group, platform, nationality, torneo_label):
    df = df_processed.copy()
    if group != "Tutti":
        df = df[df["group"] == group]
    if platform != "Tutti":
        df = df[df["platform"] == platform]
    if nationality != "Tutti":
        df = df[df["nationality"] == nationality]
    if torneo_label:
        df = df[df["torneo_label"] == torneo_label]
    return df

# ---- Update database button ----
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

# ---- Main workflow ----
df_raw = load_data()
df_prepared = prepare_dataframe(df_raw)

# Sidebar filtri
st.sidebar.header("Filtri")
placeholder = st.sidebar.empty()

group_options = ["Tutti"] + sorted(df_prepared["group"].unique())
selected_group = st.sidebar.selectbox("Gruppo", group_options)

platform_options = ["Tutti"] + sorted(df_prepared["platform"].dropna().unique())
selected_platform = st.sidebar.selectbox("Piattaforma", platform_options)

nation_options = ["Tutti"] + sorted(df_prepared["nationality"].dropna().unique())
selected_nation = st.sidebar.selectbox("Nazionalità", nation_options)

# Selezione torneo
tornei_unici = sorted(df_prepared["torneo_label"].unique())
selected_tournament = st.sidebar.radio("Torneo", [""] + tornei_unici)
placeholder.markdown(f"**Selezionato:** {selected_tournament}")

# Filtra dati
df_filtered = filter_dataframe(
    df_prepared, selected_group, selected_platform, selected_nation, selected_tournament
)

# ---- Tabella risultati ----
st.subheader("Classifica Torneo")
columns = [
    "posizione", "player", "group", "nationality", "platform",
    "r1", "r2", "r3", "r4", "strokes", "total",
    "earnings", "promotion",
    "tournament_name", "course", "purse", "dates"
]
st.dataframe(df_filtered[columns], height=600, use_container_width=True)
