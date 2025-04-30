import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
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
    FROM leaderboards AS l
    JOIN tournaments AS t ON l.tournament_id = t.id
    """
    df = pd.read_sql(query, engine)
    return df

# ---- Preparazione dati ----
@st.cache_data(ttl=600)
def prepare_dataframe(df_raw):
    df = df_raw.copy()
    # Label torneo
    df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " – " + df["tournament_name"] + " (" + df["dates"] + ")"
    # Calcolo posizione
    df["completo"] = df[["r1","r2","r3","r4"]].notnull().all(axis=1)
    completati = df[df["completo"]].copy()
    completati["posizione"] = completati["strokes"].rank(method="min").astype(int)
    incompleti = df[~df["completo"]].copy()
    incompleti["posizione"] = None
    df = pd.concat([completati, incompleti]).sort_values(by=["completo","posizione"], ascending=[False,True])
    # Format earnings and purse
    df["earnings_str"] = df["earnings"].apply(lambda x: f"${x:,}" if pd.notnull(x) else "")
    df["purse_str"] = df["purse"].apply(lambda x: f"${x:,}" if pd.notnull(x) else "")
    # Promotion icons
    def promo_icons(promo):
        if not promo or pd.isna(promo): return ""
        mapping = {"+1":"🟢","-1":"🔴","winner":"🏆","fast_track":"⚡"}
        return " ".join(mapping.get(m,"") for m in promo.split(","))
    df["promotion_icon"] = df["promotion"].apply(promo_icons)
    return df

# ---- Filtraggio dati ----
@st.cache_data()
def filter_dataframe(df, group, platform, nationality, tournament_label):
    d = df.copy()
    if group!="Tutti": d = d[d["group"]==group]
    if platform!="Tutti": d = d[d["platform"]==platform]
    if nationality!="Tutti": d = d[d["nationality"]==nationality]
    d = d[d["torneo_label"]==tournament_label]
    return d

# ---- Aggiorna database ----
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
df_prep = prepare_dataframe(df_raw)

# Sidebar filtri
st.sidebar.header("Filtri")
grp = st.sidebar.selectbox("Gruppo", ["Tutti"]+sorted(df_prep["group"].unique()))
pltf = st.sidebar.selectbox("Piattaforma", ["Tutti"]+sorted(df_prep["platform"].dropna().unique()))
nat = st.sidebar.selectbox("Nazionalità", ["Tutti"]+sorted(df_prep["nationality"].dropna().unique()))
tours = sorted(df_prep["torneo_label"].unique())
sel_tour = st.sidebar.radio("Torneo", tours)

# Filtra
df_f = filter_dataframe(df_prep, grp, pltf, nat, sel_tour)

# Tabs for table and charts
tabs = st.tabs(["Tabella","Andamento punteggi","Ripartizione Earnings","Scatter Colpi vs Earnings","Top10 Media Colpi","Heatmap Performance"])

with tabs[0]:
    st.subheader("Classifica Torneo")
    cols = ["posizione","player","group","nationality","platform","r1","r2","r3","r4","strokes","total","earnings_str","promotion_icon","course"]
    st.dataframe(df_f[cols], height=600, use_container_width=True)

# Chart 1: Andamento punteggi per giro
with tabs[1]:
    st.subheader("Andamento Punteggi per Giro")
    players = df_f["player"].unique().tolist()
    sel_players = st.multiselect("Giocatori (top 5 default)", players, default=players[:5])
    fig, ax = plt.subplots()
    for p in sel_players:
        rounds = df_f[df_f["player"]==p][["r1","r2","r3","r4"]].iloc[0].astype(float)
        ax.plot([1,2,3,4], rounds.values, marker='o', label=p)
    ax.set_xlabel("Round"); ax.set_ylabel("Colpi")
    ax.legend(); st.pyplot(fig)

# Chart 3: Ripartizione Earnings per nazionalità e piattaforma
with tabs[2]:
    st.subheader("Earnings per Nazionalità")
    df_f["earnings_val"]=df_f["earnings_str"].str.replace("[$,]","",regex=True).astype(float)
    by_nat=df_f.groupby("nationality")["earnings_val"].sum().sort_values()
    fig, ax = plt.subplots()
    ax.barh(by_nat.index, by_nat.values); ax.set_xlabel("Earnings totali")
    st.pyplot(fig)
    st.subheader("Earnings per Piattaforma")
    by_plt=df_f.groupby("platform")["earnings_val"].sum().sort_values()
    fig, ax = plt.subplots()
    ax.barh(by_plt.index, by_plt.values); ax.set_xlabel("Earnings totali")
    st.pyplot(fig)

# Chart 4: Scatter Colpi vs Earnings
with tabs[3]:
    st.subheader("Colpi vs Earnings")
    fig, ax = plt.subplots()
    ax.scatter(df_f["strokes"], df_f["earnings_val"]); ax.set_xlabel("Strokes"); ax.set_ylabel("Earnings")
    st.pyplot(fig)

# Chart 5: Top 10 Media Colpi
with tabs[4]:
    st.subheader("Top 10 Media Colpi (Stagione)")
    avg_st=df_prep.groupby("player")["strokes"].mean().nsmallest(10)
    fig, ax = plt.subplots()
    ax.barh(avg_st.index, avg_st.values); ax.set_xlabel("Media colpi")
    st.pyplot(fig)

# Chart 7: Heatmap Performance per Round
with tabs[5]:
    st.subheader("Heatmap Punteggi per Round")
    m = df_f.set_index("player")[["r1","r2","r3","r4"]].astype(float)
    fig, ax = plt.subplots()
    cax = ax.imshow(m.values, aspect="auto", interpolation="nearest")
    ax.set_xticks(range(4)); ax.set_xticklabels(["R1","R2","R3","R4"])
    ax.set_yticks(range(len(m.index))); ax.set_yticklabels(m.index)
    st.pyplot(fig)
