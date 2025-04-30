import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from time import sleep

# --- LOGIN SICURO ---
def show_login_page():
    st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="font-size: 48px;">🏌️‍♂️ TGC Tours Dashboard</h1>
            <h3 style="color: grey;">Accesso riservato agli utenti autorizzati</h3>
        </div>
    """, unsafe_allow_html=True)
    username = st.text_input("👤 Username", placeholder="Inserisci il tuo username")
    password = st.text_input("🔒 Password", type="password", placeholder="Inserisci la tua password")
    login_btn = st.button("🔑 Login")
    return username, password, login_btn

def authenticate(username, password):
    return username == st.secrets["login_username"] and password == st.secrets["login_password"]

def login_flow():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        username, password, login_btn = show_login_page()
        if login_btn:
            if authenticate(username, password):
                st.success("✅ Login avvenuto con successo!")
                sleep(1)
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("🚫 Username o password errati!")
                sleep(2)
                st.rerun()
login_flow()
if not st.session_state.get("authenticated", False):
    st.stop()

# --- IMPOSTAZIONI PAGINA ---
st.set_page_config(page_title="TGC Tours Dashboard Rework", layout="wide")
st.title("🏌️‍♂️ TGC Tours - Dashboard Ristrutturata")

# --- CONNESSIONE DB ---
connection_string = st.secrets["connection_string"]
engine = create_engine(connection_string)

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_sql("SELECT * FROM leaderboards", engine)

    # Calcola il punteggio rispetto al par
    df["total"] = df["total"] - df["par"]

    # Crea campo torneo unificato
    df["torneo_unificato"] = "[Week " + df["week"].astype(str) + "] " + df["dates"] + " – " + df["tournament_name"]

    # Ordina per data
    df = df.sort_values(by="dates")

    return df

if st.button("🔄 Aggiorna dati"):
    st.cache_data.clear()
    st.rerun()

df = load_data()

# --- SIDEBAR FILTRI ---
st.sidebar.header("🎯 Filtri")

# 🔹 Filtro Gruppo (A–L o Tutti)
gruppi = sorted(df["group"].dropna().unique())
selected_group = st.sidebar.selectbox("Gruppo", ["Tutti"] + gruppi)

# 🔹 Filtro Torneo Unificato
tornei_unici = sorted(df["torneo_unificato"].unique())
selected_torneo = st.sidebar.selectbox("Torneo", ["Tutti"] + tornei_unici)

# 🔹 Filtro Piattaforma
piattaforme = sorted(df["platform"].dropna().unique())
selected_platforms = st.sidebar.multiselect("Piattaforme", piattaforme)

# 🔹 Filtro Nazionalità
nazioni = sorted(df["nationality"].dropna().unique())
selected_nations = st.sidebar.multiselect("Nazionalità", nazioni)

# --- FILTRAGGIO DATI ---
filtered_df = df.copy()

if selected_group != "Tutti":
    filtered_df = filtered_df[filtered_df["group"] == selected_group]

if selected_torneo != "Tutti":
    filtered_df = filtered_df[filtered_df["torneo_unificato"] == selected_torneo]

if selected_platforms:
    filtered_df = filtered_df[filtered_df["platform"].isin(selected_platforms)]

if selected_nations:
    filtered_df = filtered_df[filtered_df["nationality"].isin(selected_nations)]

# --- Rinomina campo 'total' come punteggio relativo al par ---
filtered_df["score_vs_par"] = filtered_df["total"].apply(lambda x: f"{x:+d}")

# --- SELEZIONE COLONNE DA MOSTRARE ---
columns_to_display = [
    "player", "group", "tournament_name", "dates", "week", "course",
    "platform", "nationality", "score_vs_par", "r1", "r2", "r3", "r4", "earnings"
]

st.subheader("📋 Risultati Tornei")
st.dataframe(filtered_df[columns_to_display], use_container_width=True)
