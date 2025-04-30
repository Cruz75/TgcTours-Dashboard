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

# ---- Caricamento e preparazione dati ----
@st.cache_data(ttl=600)
def load_and_prepare():
    df = pd.read_sql(
        """
        SELECT l.*, t.week, t.dates, t.tournament_name, t.course, t.purse
        FROM leaderboards l
        JOIN tournaments t ON l.tournament_id = t.id
        """, engine
    )
    df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " – " + df["tournament_name"] + " (" + df["dates"] + ")"
    df["earnings_val"] = df["earnings"].replace("[\$,]", "", regex=True).astype(float)
    return df

df = load_and_prepare()

# ---- Sidebar filtri ----
st.sidebar.header("Filtri Generali")
grp = st.sidebar.selectbox("Gruppo", ["Tutti"] + sorted(df["group"].unique()))
pltf = st.sidebar.selectbox("Piattaforma", ["Tutti"] + sorted(df["platform"].dropna().unique()))
nat = st.sidebar.selectbox("Nazionalità", ["Tutti"] + sorted(df["nationality"].dropna().unique()))
tour = st.sidebar.selectbox("Torneo", sorted(df["torneo_label"].unique()))

# Applicazione filtri
df_f = df.copy()
if grp != "Tutti": df_f = df_f[df_f["group"] == grp]
if pltf != "Tutti": df_f = df_f[df_f["platform"] == pltf]
if nat != "Tutti": df_f = df_f[df_f["nationality"] == nat]
df_t = df_f[df_f["torneo_label"] == tour]

tabs = st.tabs(["Tabella", "1️⃣ Andamento Giro", "2️⃣ Difficoltà Campi", 
                "3️⃣ Montepremi", "4️⃣ Scatter Strokes vs Earnings", 
                "5️⃣ Top10 Media Colpi", "7️⃣ Heatmap Performance"])

# Tabella
with tabs[0]:
    st.subheader("Classifica Torneo")
    cols = ["posizione","player","group","nationality","platform",
            "r1","r2","r3","r4","strokes","total","earnings","promotion","course"]
    st.dataframe(df_t[cols], height=500, use_container_width=True)

# 1. Andamento punteggi per giro
with tabs[1]:
    st.subheader("Andamento dei punteggi per giro")
    players = df_t["player"].unique().tolist()
    with st.expander("Opzioni Grafico"):
        top_n = st.number_input("Numero di giocatori (ordine per strokes)", min_value=1, max_value=len(players), value=5)
        sorted_players = df_t.nsmallest(top_n, "strokes")["player"].tolist()
        sel_players = st.multiselect("Seleziona giocatori", players, default=sorted_players)
    fig, ax = plt.subplots(figsize=(6,4))
    for p in sel_players:
        vals = df_t[df_t["player"] == p][["r1","r2","r3","r4"]].iloc[0].astype(float).values
        ax.plot([1,2,3,4], vals, marker='o', label=p)
    ax.set_xlabel("Round"); ax.set_ylabel("Colpi"); ax.set_xticks([1,2,3,4])
    ax.tick_params(labelsize=8); ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout(); st.pyplot(fig)

# 2. Difficoltà Campi: Boxplot strokes per gruppo/tour
with tabs[2]:
    st.subheader("Distribuzione Colpi Totali (Difficoltà Campo)")
    by = st.selectbox("Raggruppa per", ["group", "tournament_name"], index=0)
    fig, ax = plt.subplots(figsize=(6,4))
    df_grouped = df_f if by=="group" else df_t
    data = [df_grouped[df_grouped[by]==g]["strokes"].dropna() for g in df_grouped[by].unique()]
    labels = df_grouped[by].unique()
    ax.boxplot(data, labels=labels, vert=False)
    ax.set_xlabel("Strokes"); ax.tick_params(labelsize=8)
    fig.tight_layout(); st.pyplot(fig)

# 3. Ripartizione Montepremi
with tabs[3]:
    st.subheader("Ripartizione Montepremi")
    kind = st.radio("Mostra per:", ("Nazionalità", "Piattaforma"))
    if kind=="Nazionalità":
        series = df_f.groupby("nationality")["earnings_val"].sum().nlargest(10)
    else:
        series = df_f.groupby("platform")["earnings_val"].sum().nlargest(10)
    fig, ax = plt.subplots(figsize=(6,4))
    ax.barh(series.index, series.values)
    ax.set_xlabel("Earnings"); ax.tick_params(labelsize=8)
    fig.tight_layout(); st.pyplot(fig)

# 4. Scatter strokes vs earnings
with tabs[4]:
    st.subheader("Scatter: Colpi vs Earnings")
    fig, ax = plt.subplots(figsize=(6,4))
    ax.scatter(df_t["strokes"], df_t["earnings_val"], alpha=0.7)
    ax.set_xlabel("Strokes"); ax.set_ylabel("Earnings"); ax.tick_params(labelsize=8)
    fig.tight_layout(); st.pyplot(fig)

# 5. Top 10 media colpi
with tabs[5]:
    st.subheader("Top 10 Media Colpi (Stagione)")
    n = st.slider("Numero di giocatori", 5, 20, 10)
    avg = df_f.groupby("player")["strokes"].mean().nsmallest(n)
    fig, ax = plt.subplots(figsize=(6,4))
    ax.barh(avg.index, avg.values)
    ax.set_xlabel("Media colpi"); ax.tick_params(labelsize=8)
    fig.tight_layout(); st.pyplot(fig)

# 7. Heatmap performance per round
with tabs[6]:
    st.subheader("Heatmap Punteggi per Round")
    maxp = st.slider("Numero di giocatori", 5, len(df_t), 10)
    m = df_t.sort_values("strokes").head(maxp).set_index("player")[["r1","r2","r3","r4"]].astype(float)
    fig, ax = plt.subplots(figsize=(6, maxp*0.4))
    c = ax.imshow(m.values, aspect="auto", cmap='RdYlGn_r')
    ax.set_xticks(range(4)); ax.set_xticklabels(["R1","R2","R3","R4"])
    ax.set_yticks(range(len(m.index))); ax.set_yticklabels(m.index)
    fig.colorbar(c, ax=ax, orientation='vertical', fraction=0.046)
    fig.tight_layout(); st.pyplot(fig)
