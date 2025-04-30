import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

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
    FROM leaderboards l
    JOIN tournaments t ON l.tournament_id = t.id
    """
    return pd.read_sql(query, engine)

# ---- Preparazione dati ----
@st.cache_data(ttl=600)
def prepare_dataframe(df_raw):
    df = df_raw.copy()
    df["torneo_label"] = (
        df["week"].astype(str).str.zfill(2)
        + " – "
        + df["tournament_name"]
        + " ("
        + df["dates"]
        + ")"
    )
    # Convert earnings to numeric
    df["earnings_val"] = (
        df["earnings"]
          .fillna("")                     
          .astype(str)                    
          .str.replace("[$,]", "", regex=True)
          .replace("", "0")               
          .astype(float)                  
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
    return df

# ---- Filtraggio dati ----
@st.cache_data()
def filter_dataframe(df, group, platform, nationality, tournament_label):
    df_f = df.copy()
    if group != "Tutti":
        df_f = df_f[df_f["group"] == group]
    if platform != "Tutti":
        df_f = df_f[df_f["platform"] == platform]
    if nationality != "Tutti":
        df_f = df_f[df_f["nationality"] == nationality]
    df_f = df_f[df_f["torneo_label"] == tournament_label]
    return df_f

# ---- Aggiorna database ----
def update_all():
    import scraper_update_fixed; scraper_update_fixed.main()

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
df_prep = prepare_dataframe(df_raw)

# Sidebar filtri
st.sidebar.header("Filtri")
grp = st.sidebar.selectbox("Gruppo", ["Tutti"] + sorted(df_prep["group"].unique()))
pltf = st.sidebar.selectbox("Piattaforma", ["Tutti"] + sorted(df_prep["platform"].dropna().unique()))
nat = st.sidebar.selectbox("Nazionalità", ["Tutti"] + sorted(df_prep["nationality"].dropna().unique()))
tours = sorted(df_prep["torneo_label"].unique())
sel_tour = st.sidebar.radio("Torneo", tours)

# Filtra dataframe
df_filtered = filter_dataframe(df_prep, grp, pltf, nat, sel_tour)

# ---- Visualizzazione tramite Tabs ----
tabs = st.tabs([
    "🔢 Classifica",
    "📈 Andamento Giro",
    "📊 Difficoltà campi",
    "💰 Montepremi",
    "🎯 Strokes vs Earnings",
    "🏆 Top10 Media Colpi",
    "🔥 Heatmap Round"
])

# Tabella
with tabs[0]:
    st.subheader("Classifica Torneo")
    cols = [
        "posizione", "player", "group", "nationality", "platform",
        "r1", "r2", "r3", "r4", "strokes", "total",
        "earnings", "promotion",
        "tournament_name", "course", "purse", "dates"
    ]
    st.dataframe(df_filtered[cols], height=400, use_container_width=True)

# Grafici...
# (resto del file identico alla versione pretty2)
