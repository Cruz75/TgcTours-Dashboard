import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine

# ---- Configurazione pagina ----
st.set_page_config(page_title="TGC Tours Dashboard con Grafici", layout="wide")
st.title("🏌️‍♂️ TGC Tours Dashboard 2025")
st.markdown("Dashboard con statistiche e grafici avanzati – esclusi Istogramma strokes vs par e WGR.")

# ---- Connessione e caricamento dati ----
engine = create_engine(st.secrets["connection_string"])

@st.cache_data(ttl=600)
def load_data():
    df = pd.read_sql(
        """
        SELECT l.*, t.week, t.dates, t.tournament_name, t.course, t.purse
        FROM leaderboards l
        JOIN tournaments t ON l.tournament_id = t.id
        """, engine)
    # Estrai date
    def estrai_date_range(date_str):
        try:
            start, end = date_str.split(" - ")
            start = pd.to_datetime(start, format="%m/%d")
            end = pd.to_datetime(end, format="%m/%d")
            return start, end
        except:
            return None, None
    df["start_date"], df["end_date"] = zip(*df["dates"].apply(estrai_date_range))
    # Prepara total come over/under se già presente, altrimenti usa strokes
    if "over_under" in df.columns:
        df["total_rel"] = df["over_under"]
    else:
        df["total_rel"] = df["strokes"]
    return df

df = load_data()

# ---- Sidebar filtri ----
st.sidebar.header("Filtri")
group = st.sidebar.selectbox("Gruppo", ["Tutti"] + sorted(df["group"].unique()))
platform = st.sidebar.selectbox("Piattaforma", ["Tutti"] + sorted(df["platform"].dropna().unique()))
nation = st.sidebar.selectbox("Nazionalità", ["Tutti"] + sorted(df["nationality"].dropna().unique()))
tournament = st.sidebar.radio("Torneo", sorted(df["tournament_name"].unique()))

# Applica filtri
df_f = df.copy()
if group!="Tutti": df_f = df_f[df_f["group"]==group]
if platform!="Tutti": df_f = df_f[df_f["platform"]==platform]
if nation!="Tutti": df_f = df_f[df_f["nationality"]==nation]
df_t = df_f[df_f["tournament_name"]==tournament]

# ---- Selezione giocatori per grafico 1 e 6 ----
players = df_t["player"].unique().tolist()
selected_players = st.multiselect("Seleziona giocatori per grafico 1", players, default=players[:5])

# ---- 1. Andamento dei punteggi per giro ----
st.subheader("1. Andamento punteggi per giro")
fig, ax = plt.subplots()
for p in selected_players:
    rounds = df_t[df_t["player"]==p][["r1","r2","r3","r4"]].iloc[0].astype(float).values
    ax.plot([1,2,3,4], rounds, marker='o', label=p)
ax.set_xlabel("Round")
ax.set_ylabel("Colpi")
ax.legend()
st.pyplot(fig)

# ---- 3. Ripartizione monte premi ----
st.subheader("3. Earnings per Nazionalità")
earn_nation = df_f.groupby("nationality")["earnings"].sum().replace('[\$,]', '', regex=True).astype(float)
fig, ax = plt.subplots()
ax.barh(earn_nation.index, earn_nation.values)
ax.set_xlabel("Earnings totali")
st.pyplot(fig)

st.subheader("3b. Earnings per Piattaforma")
earn_plat = df_f.groupby("platform")["earnings"].sum().replace('[\$,]', '', regex=True).astype(float)
fig, ax = plt.subplots()
ax.barh(earn_plat.index, earn_plat.values)
ax.set_xlabel("Earnings totali")
st.pyplot(fig)

# ---- 4. Scatter strokes vs earnings ----
st.subheader("4. Colpi vs Earnings")
fig, ax = plt.subplots()
x = df_t["strokes"].astype(float)
y = df_t["earnings"].replace('[\$,]', '', regex=True).astype(float)
ax.scatter(x, y)
ax.set_xlabel("Strokes")
ax.set_ylabel("Earnings")
st.pyplot(fig)

# ---- 5. Top 10 giocatori per media colpi ----
st.subheader("5. Top 10 media colpi (Stagione)")
avg_strokes = df_f.groupby("player")["strokes"].mean().nsmallest(10)
fig, ax = plt.subplots()
ax.barh(avg_strokes.index, avg_strokes.values)
ax.set_xlabel("Media colpi")
st.pyplot(fig)

# ---- 7. Heatmap performance per round ----
st.subheader("7. Heatmap punteggi per round")
heat = df_t.pivot(index="player", columns=["r1","r2","r3","r4"], values="r1") # wrong structure
# Instead construct matrix manually:
m = df_t.set_index("player")[["r1","r2","r3","r4"]].astype(float)
fig, ax = plt.subplots()
cax = ax.imshow(m.values, aspect="auto", interpolation="nearest")
ax.set_xticks(range(4))
ax.set_xticklabels(["R1","R2","R3","R4"])
ax.set_yticks(range(len(m.index)))
ax.set_yticklabels(m.index)
st.pyplot(fig)
