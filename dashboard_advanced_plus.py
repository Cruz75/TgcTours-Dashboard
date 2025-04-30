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
    df = pd.read_sql(query, engine)
    return df

# ---- Preparazione dati ----
@st.cache_data(ttl=600)
def prepare_dataframe(df_raw):
    df = df_raw.copy()
    df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " – " + df["tournament_name"] + " (" + df["dates"] + ")"
    df["earnings_val"] = df["earnings"].str.replace("[$,]", "", regex=True).astype(float)
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

# 1. Andamento punteggi per giro
with tabs[1]:
    st.subheader("Andamento Punteggi per Giro")
    players = df_filtered["player"].tolist()
    default_players = df_filtered.nsmallest(5, "strokes")["player"].tolist()
    sel_players = st.multiselect("Seleziona giocatori", players, default=default_players)
    fig, ax = plt.subplots(figsize=(6,3))
    for p in sel_players:
        vals = df_filtered[df_filtered["player"] == p][["r1","r2","r3","r4"]].iloc[0].astype(float).values
        ax.plot([1,2,3,4], vals, marker='o', label=p)
    ax.set_xticks([1,2,3,4])
    ax.set_xlabel("Round")
    ax.set_ylabel("Colpi")
    ax.legend(fontsize=6)
    fig.tight_layout()
    st.pyplot(fig)

# 2. Boxplot difficoltà campi
with tabs[2]:
    st.subheader("Difficoltà dei Campi (Boxplot Strokes)")
    by = st.selectbox("Raggruppa per", ["group", "tournament_name"])
    groups = sorted(df_filtered[by].unique())
    data = [df_filtered[df_filtered[by]==g]["strokes"].dropna() for g in groups]
    fig, ax = plt.subplots(figsize=(6,3))
    ax.boxplot(data, labels=groups, vert=False)
    ax.set_xlabel("Strokes")
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    st.pyplot(fig)

# 3. Montepremi
with tabs[3]:
    st.subheader("Ripartizione Montepremi")
    kind = st.radio("Mostra per", ("Nazionalità", "Piattaforma"), horizontal=True)
    # Usa la colonna numerica earnings_val
    if kind == "Nazionalità":
        series = df_filtered.groupby("nationality")["earnings_val"].sum().nlargest(10)
    else:
        series = df_filtered.groupby("platform")["earnings_val"].sum().nlargest(10)
    fig, ax = plt.subplots(figsize=(6,3))
    ax.barh(series.index, series.values)
    ax.set_xlabel("Earnings")
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    st.pyplot(fig)

# 4. Scatter strokes vs earnings
with tabs[4]:
    st.subheader("Scatter: Colpi vs Earnings")
    fig, ax = plt.subplots(figsize=(6,3))
    y = df_filtered["earnings_val"]
    ax.scatter(df_filtered["strokes"], y, alpha=0.7)
    ax.set_xlabel("Strokes")
    ax.set_ylabel("Earnings")
    fig.tight_layout()
    st.pyplot(fig)

# 5. Top10 media colpi
with tabs[5]:
    st.subheader("Top 10 Media Colpi")
    n = st.slider("Numero di giocatori", min_value=5, max_value=20, value=10)
    avg = df_prep.groupby("player")["strokes"].mean().nsmallest(n)
    fig, ax = plt.subplots(figsize=(6,3))
    ax.barh(avg.index, avg.values)
    ax.set_xlabel("Media colpi")
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    st.pyplot(fig)

# 6. Heatmap performance per round
with tabs[6]:
    st.subheader("Heatmap Punteggi per Round")
    maxp = st.slider("Numero di giocatori", 5, len(df_filtered), 10)
    m = df_filtered.sort_values("strokes").head(maxp).set_index("player")[["r1","r2","r3","r4"]].astype(float)
    fig, ax = plt.subplots(figsize=(6, maxp*0.2))
    c = ax.imshow(m.values, aspect="auto", cmap="RdYlGn_r")
    ax.set_xticks(range(4))
    ax.set_xticklabels(["R1","R2","R3","R4"])
    ax.set_yticks(range(len(m.index)))
    ax.set_yticklabels(m.index, fontsize=6)
    fig.colorbar(c, ax=ax, orientation="vertical", fraction=0.046)
    fig.tight_layout()
    st.pyplot(fig)
