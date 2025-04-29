# --- IMPORT ---
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from time import sleep

# --- LOGIN GRAFICO ---
def show_login_page():
    st.markdown(
        """
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="font-size: 48px;">🏌️‍♂️ TGC Tours Dashboard</h1>
            <h3 style="color: grey;">Accesso riservato agli utenti autorizzati</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
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
    else:
        pass

login_flow()

if not st.session_state.get("authenticated", False):
    st.stop()

# --- DASHBOARD CONFIG ---
st.set_page_config(page_title="TGC Tours Dashboard Plus", layout="wide")
st.title("🏌️‍♂️ TGC Tours - Dashboard Plus 2025")

# --- CONNESSIONE DATABASE ---
connection_string = st.secrets["connection_string"]
engine = create_engine(connection_string)

# --- CARICAMENTO DATI ---
@st.cache_data(ttl=300)
def load_data():
    query = "SELECT * FROM leaderboards"
    df = pd.read_sql(query, engine)
    return df

# Pulsante aggiorna
if st.button("🔄 Aggiorna dati dal database"):
    st.cache_data.clear()
    st.rerun()

# Carica dati
df = load_data()

# --- SIDEBAR: Filtri ---
st.sidebar.header("🔎 Filtri Dati")
tournament_filter = st.sidebar.multiselect("Torneo", sorted(df['tournament_name'].unique()))
platform_filter = st.sidebar.multiselect("Piattaforma", sorted(df['platform'].dropna().unique()))
nationality_filter = st.sidebar.multiselect("Nazionalità", sorted(df['nationality'].dropna().unique()))
week_filter = st.sidebar.multiselect("Settimana", sorted(df['week'].dropna().unique()))

# Applica filtri
filtered_df = df.copy()
if tournament_filter:
    filtered_df = filtered_df[filtered_df['tournament_name'].isin(tournament_filter)]
if platform_filter:
    filtered_df = filtered_df[filtered_df['platform'].isin(platform_filter)]
if nationality_filter:
    filtered_df = filtered_df[filtered_df['nationality'].isin(nationality_filter)]
if week_filter:
    filtered_df = filtered_df[filtered_df['week'].isin(week_filter)]

# --- FUNZIONI GRAFICI AVANZATI ---

def plot_wgr_progression(df):
    st.subheader("📈 World Golf Ranking Progression")
    players = st.multiselect("Seleziona i giocatori:", sorted(df['player'].unique()), key="wgr_select")
    if players:
        wgr_df = df[df['player'].isin(players)]
        wgr_df = wgr_df.dropna(subset=['wgr'])
        fig = px.line(
            wgr_df.sort_values('dates'),
            x='dates', y='wgr', color='player',
            title="Progressione WGR nel tempo",
            markers=True
        )
        fig.update_layout(yaxis_title="World Golf Ranking (più basso è meglio)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Seleziona almeno un giocatore.")

def plot_player_rounds(df):
    st.subheader("🏌️‍♂️ Players Round Over Time")
    players = st.multiselect("Scegli il giocatore:", sorted(df['player'].unique()), key="round_select")
    if players:
        rounds_df = df[df['player'].isin(players)]
        rounds_melted = pd.melt(
            rounds_df,
            id_vars=['player', 'dates', 'tournament_name'],
            value_vars=['r1', 'r2', 'r3', 'r4'],
            var_name='round',
            value_name='score'
        ).dropna()
        fig = px.line(
            rounds_melted.sort_values('dates'),
            x='dates', y='score', color='player', line_group='round',
            title="Andamento punteggi Round dopo Round",
            markers=True
        )
        fig.update_layout(yaxis_title="Punteggio Round (minore è meglio)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Seleziona almeno un giocatore.")

# --- LAYOUT TABS ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏆 Leaderboard",
    "📈 Punteggi",
    "🌍 Distribuzioni",
    "📅 Timeline Tornei",
    "🎯 Analisi WGR",
    "🏆 Top 10 + Best Round",
    "📈 Analisi Avanzate"
])

# --- CONTENUTI TABS ---
with tab1:
    st.subheader("🏆 Leaderboard Completa")
    st.dataframe(filtered_df, use_container_width=True)

with tab2:
    st.subheader("📈 Analisi Punteggi")
    col1, col2 = st.columns(2)
    with col1:
        fig_score = px.histogram(filtered_df, x="total", nbins=30, title="Distribuzione Totale Punteggi")
        st.plotly_chart(fig_score, use_container_width=True)
    with col2:
        score_mean = filtered_df.groupby('tournament_name')['total'].mean().reset_index()
        fig_mean = px.bar(score_mean, x="tournament_name", y="total", title="Punteggio Medio per Torneo", text_auto=True)
        st.plotly_chart(fig_mean, use_container_width=True)

with tab3:
    st.subheader("🌍 Distribuzioni Piattaforme e Nazionalità")
    col1, col2 = st.columns(2)
    with col1:
        fig_platform = px.pie(filtered_df, names="platform", title="Distribuzione Giocatori per Piattaforma")
        st.plotly_chart(fig_platform, use_container_width=True)
    with col2:
        fig_nationality = px.pie(filtered_df, names="nationality", title="Distribuzione Giocatori per Nazionalità")
        st.plotly_chart(fig_nationality, use_container_width=True)

with tab4:
    st.subheader("📅 Andamento Totale Punteggi nel Tempo")
    if 'dates' in filtered_df.columns and 'total' in filtered_df.columns:
        timeline_df = filtered_df.groupby('dates')['total'].mean().reset_index()
        fig_timeline = px.line(timeline_df, x="dates", y="total", title="Media Totale Punteggi per Data Torneo")
        st.plotly_chart(fig_timeline, use_container_width=True)

with tab5:
    st.subheader("🎯 World Golf Ranking Analisi")
    if 'wgr' in filtered_df.columns:
        wgr_df = filtered_df.dropna(subset=['wgr'])
        col1, col2 = st.columns(2)
        with col1:
            fig_wgr = px.histogram(wgr_df, x="wgr", nbins=30, title="Distribuzione World Golf Ranking")
            st.plotly_chart(fig_wgr, use_container_width=True)
        with col2:
            avg_wgr = wgr_df.groupby('tournament_name')['wgr'].mean().reset_index()
            fig_avg_wgr = px.bar(avg_wgr, x="tournament_name", y="wgr", title="Media WGR per Torneo", text_auto=True)
            st.plotly_chart(fig_avg_wgr, use_container_width=True)

with tab6:
    st.subheader("🏆 Top 10 Migliori Giocatori")
    top10 = filtered_df[['player', 'platform', 'total', 'tournament_name']].sort_values(by='total').head(10)
    st.dataframe(top10, use_container_width=True)

    st.subheader("🏅 Best Round Assoluto")
    best_rounds = pd.melt(
        filtered_df,
        id_vars=["player", "platform", "tournament_name"],
        value_vars=["r1", "r2", "r3", "r4"],
        var_name="round",
        value_name="score"
    ).sort_values(by="score").dropna().head(10)
    st.dataframe(best_rounds, use_container_width=True)

with tab7:
    st.subheader("📈 Analisi Avanzate - WGR e Round")
    plot_wgr_progression(filtered_df)
    plot_player_rounds(filtered_df)

# --- FOOTER ---
st.caption("TGC Tours 2025 | Dashboard Plus v2 creata con ❤️ usando Streamlit & Plotly 🚀")
