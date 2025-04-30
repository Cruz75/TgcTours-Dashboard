import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import matplotlib.pyplot as plt

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
selected_tournament = st.sidebar.radio("Torneo", tornei_unici)
placeholder.markdown(f"**Selezionato:** {selected_tournament}")

# Filtra dati
df_filtered = filter_dataframe(
    df_prepared, selected_group, selected_platform, selected_nation, selected_tournament
)


# ---- Ricalcolo posizione relativo alla selezione ----
df_filtered["completo"] = df_filtered[["r1", "r2", "r3", "r4"]].notnull().all(axis=1)
completi = df_filtered[df_filtered["completo"]].copy()
completi["posizione"] = completi["strokes"].rank(method="min").astype(int)
incompleti = df_filtered[~df_filtered["completo"]].copy()
incompleti["posizione"] = None
df_filtered = pd.concat([completi, incompleti]).sort_values(by=["completo", "posizione"], ascending=[False, True])


# ---- Visualizzazione tramite Tabs ----
tabs = st.tabs([
    "🔢 Classifica",
    "📈 Andamento giri",
    "📊 Difficoltà campi",
    "💰 Montepremi",
    "🎯 Strokes vs Earnings",
    "🏆 Top10 Media Colpi",
    "🔥 Heatmap Round"
])

# Tabella
with tabs[0]:
    st.subheader("Classifica Torneo")
    columns = [
        "posizione", "player", "group", "nationality", "platform",
        "r1", "r2", "r3", "r4", "strokes", "total",
        "earnings", "promotion",
        "tournament_name", "course", "purse", "dates"
    ]
    st.dataframe(df_filtered[columns], height=400, use_container_width=True)

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
    ax.set_xticks([1,2,3,4]); ax.set_xlabel("Round"); ax.set_ylabel("Colpi")
    ax.legend(fontsize=6); fig.tight_layout(); st.pyplot(fig)

# 2. Boxplot difficoltà campi
with tabs[2]:
    st.subheader("Difficoltà dei Campi (Boxplot Strokes)")
    by = st.selectbox("Raggruppa per", ["group", "tournament_name"])
    data_groups = df_filtered if by=="group" else df_filtered
    groups = sorted(df_filtered[by].unique())
    data = [df_filtered[df_filtered[by]==g]["strokes"].dropna() for g in groups]
    fig, ax = plt.subplots(figsize=(6,3))
    ax.boxplot(data, labels=groups, vert=False)
    ax.set_xlabel("Strokes"); ax.tick_params(labelsize=6)
    fig.tight_layout(); st.pyplot(fig)

# 3. Montepremi
with tabs[3]:
    st.subheader("Ripartizione Montepremi")
    kind = st.radio("Mostra per", ("Nazionalità","Piattaforma"), horizontal=True)
    if kind=="Nazionalità":
        # Assicurati di avere una colonna numerica earnings_val
df_filtered["earnings_val"] = (
    df_filtered["earnings"]
      .str.replace("[$,]", "", regex=True)
      .astype(float)
)
# Ora raggruppa su quella
series = df_filtered.groupby("nationality")["earnings_val"] \
    .sum() \
    .nlargest(10)
    else:
        # Assicurati di avere una colonna numerica earnings_val
df_filtered["earnings_val"] = (
    df_filtered["earnings"]
      .str.replace("[$,]", "", regex=True)
      .astype(float)
)
# Ora raggruppa su quella
series = df_filtered.groupby("platform")["earnings_val"] \
    .sum() \
    .nlargest(10)

    fig, ax = plt.subplots(figsize=(6,3))
    ax.barh(series.index, series.values)
    ax.set_xlabel("Earnings"); ax.tick_params(labelsize=6)
    fig.tight_layout(); st.pyplot(fig)

# 4. Scatter strokes vs earnings
with tabs[4]:
    st.subheader("Scatter: Colpi vs Earnings")
    fig, ax = plt.subplots(figsize=(6,3))
    y = df_filtered["earnings"].replace('[\$,]','',regex=True).astype(float)
    ax.scatter(df_filtered["strokes"], y, alpha=0.7)
    ax.set_xlabel("Strokes"); ax.set_ylabel("Earnings")
    fig.tight_layout(); st.pyplot(fig)

# 5. Top10 media colpi
with tabs[5]:
    st.subheader("Top 10 Media Colpi")
    n = st.slider("Numero di giocatori", min_value=5, max_value=20, value=10)
    avg = df_filtered.groupby("player")["strokes"].mean().nsmallest(n)
    fig, ax = plt.subplots(figsize=(6,3))
    ax.barh(avg.index, avg.values)
    ax.set_xlabel("Media colpi"); ax.tick_params(labelsize=6)
    fig.tight_layout(); st.pyplot(fig)

# 6. Heatmap performance per round
with tabs[6]:
    st.subheader("Heatmap Punteggi per Round")
    maxp = st.slider("Numero di giocatori", 5, len(df_filtered), 10)
    m = df_filtered.sort_values("strokes").head(maxp).set_index("player")[["r1","r2","r3","r4"]].astype(float)
    fig, ax = plt.subplots(figsize=(6, maxp*0.2))
    c = ax.imshow(m.values, aspect="auto", cmap="RdYlGn_r")
    ax.set_xticks(range(4)); ax.set_xticklabels(["R1","R2","R3","R4"])
    ax.set_yticks(range(len(m.index))); ax.set_yticklabels(m.index, fontsize=6)
    fig.colorbar(c, ax=ax, orientation="vertical", fraction=0.046)
    fig.tight_layout(); st.pyplot(fig)

