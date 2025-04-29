import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px
from time import sleep

# --- LOGIN GRAFICO ---
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

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="TGC Tours Dashboard Pro", layout="wide")
st.title("🏌️‍♂️ TGC Tours - Dashboard Pro 2025")

# --- SELEZIONE TEMA ---
theme = st.sidebar.radio("🎨 Tema grafico", ["Light", "Dark"])
template = "plotly_dark" if theme == "Dark" else "plotly_white"

# --- CONNESSIONE DB ---
connection_string = st.secrets["connection_string"]
engine = create_engine(connection_string)

@st.cache_data(ttl=300)
def load_data():
    return pd.read_sql("SELECT * FROM leaderboards", engine)

if st.button("🔄 Aggiorna dati"):
    st.cache_data.clear()
    st.rerun()

df = load_data()

# --- FILTRI ---
st.sidebar.header("🔎 Filtri Dati")
tournament_filter = st.sidebar.multiselect("Torneo", sorted(df['tournament_name'].unique()))
platform_filter = st.sidebar.multiselect("Piattaforma", sorted(df['platform'].dropna().unique()))
nationality_filter = st.sidebar.multiselect("Nazionalità", sorted(df['nationality'].dropna().unique()))
week_filter = st.sidebar.multiselect("Settimana", sorted(df['week'].dropna().unique()))

filtered_df = df.copy()
if tournament_filter:
    filtered_df = filtered_df[filtered_df['tournament_name'].isin(tournament_filter)]
if platform_filter:
    filtered_df = filtered_df[filtered_df['platform'].isin(platform_filter)]
if nationality_filter:
    filtered_df = filtered_df[filtered_df['nationality'].isin(nationality_filter)]
if week_filter:
    filtered_df = filtered_df[filtered_df['week'].isin(week_filter)]
# --- GRAFICI AVANZATI ---

def plot_wgr_progression(df):
    st.subheader("📈 World Golf Ranking Progression")
    players = st.multiselect("Giocatori da tracciare:", sorted(df['player'].unique()), key="wgr_select")
    if players:
        wgr_df = df[df['player'].isin(players)].dropna(subset=['wgr'])
        fig = px.line(wgr_df.sort_values('dates'), x='dates', y='wgr', color='player',
                      title="Progressione WGR", markers=True, template=template)
        fig.update_layout(yaxis_title="World Golf Ranking")
        st.plotly_chart(fig, use_container_width=True)

def plot_player_rounds(df):
    st.subheader("🏌️‍♂️ Players Round Over Time")
    players = st.multiselect("Giocatori:", sorted(df['player'].unique()), key="rounds")
    if players:
        r_df = df[df['player'].isin(players)]
        melted = pd.melt(
            r_df, id_vars=["player", "dates", "tournament_name"],
            value_vars=["r1", "r2", "r3", "r4"],
            var_name="round", value_name="score"
        ).dropna()
        fig = px.line(melted.sort_values("dates"), x="dates", y="score", color="player",
                      line_group="round", title="Round dopo Round", markers=True, template=template)
        st.plotly_chart(fig, use_container_width=True)

def plot_top_nations(df):
    st.subheader("🌍 Migliori 5 Nazioni per Media WGR")
    nation_df = df.dropna(subset=["wgr"])
    top_nations = nation_df.groupby("nationality")["wgr"].mean().nsmallest(5).reset_index()
    fig = px.bar(top_nations, x="nationality", y="wgr", title="Top 5 Nazioni", text_auto=True, template=template)
    st.plotly_chart(fig, use_container_width=True)

def plot_platform_scores(df):
    st.subheader("🎮 Media Totale per Piattaforma")
    plat_df = df.dropna(subset=["total", "platform"])
    avg_df = plat_df.groupby("platform")["total"].mean().sort_values().reset_index()
    fig = px.bar(avg_df, x="platform", y="total", title="Media Punteggi per Piattaforma", text_auto=True, template=template)
    fig.update_layout(yaxis_title="Punteggio medio (minore è meglio)")
    st.plotly_chart(fig, use_container_width=True)

# --- TABS LAYOUT ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🏆 Leaderboard", "📈 Punteggi", "🌍 Distribuzioni",
    "📅 Timeline", "🎯 Analisi WGR", "🏅 Top 10 / Best Round",
    "📊 Avanzate", "🌐 Nazionalità / Piattaforme"
])

with tab1:
    st.subheader("🏆 Leaderboard")
    st.dataframe(filtered_df, use_container_width=True)

with tab2:
    st.subheader("📈 Punteggi Totali")
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.histogram(filtered_df, x="total", nbins=30, title="Distribuzione Totale", template=template)
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        mean_df = filtered_df.groupby("tournament_name")["total"].mean().reset_index()
        fig2 = px.bar(mean_df, x="tournament_name", y="total", title="Media per Torneo", text_auto=True, template=template)
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("🌍 Distribuzioni")
    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.pie(filtered_df, names="platform", title="Piattaforme", template=template)
        st.plotly_chart(fig3, use_container_width=True)
    with col2:
        fig4 = px.pie(filtered_df, names="nationality", title="Nazionalità", template=template)
        st.plotly_chart(fig4, use_container_width=True)

with tab4:
    st.subheader("📅 Timeline Tornei")
    timeline = filtered_df.groupby("dates")["total"].mean().reset_index()
    fig5 = px.line(timeline, x="dates", y="total", title="Punteggio Medio per Data", template=template)
    st.plotly_chart(fig5, use_container_width=True)

with tab5:
    st.subheader("🎯 Analisi WGR")
    wgr_df = filtered_df.dropna(subset=["wgr"])
    fig6 = px.histogram(wgr_df, x="wgr", nbins=30, title="Distribuzione WGR", template=template)
    st.plotly_chart(fig6, use_container_width=True)

    mean_wgr = wgr_df.groupby("tournament_name")["wgr"].mean().reset_index()
    fig7 = px.bar(mean_wgr, x="tournament_name", y="wgr", title="Media WGR per Torneo", text_auto=True, template=template)
    st.plotly_chart(fig7, use_container_width=True)

with tab6:
    st.subheader("🏅 Top 10 Totale")
    top10 = filtered_df[['player', 'platform', 'total', 'tournament_name']].sort_values("total").head(10)
    st.dataframe(top10, use_container_width=True)

    st.subheader("🎯 Best Round Assoluto")
    best = pd.melt(filtered_df, id_vars=["player", "platform", "tournament_name"],
                   value_vars=["r1", "r2", "r3", "r4"],
                   var_name="round", value_name="score").dropna().sort_values("score").head(10)
    st.dataframe(best, use_container_width=True)

with tab7:
    st.subheader("📈 Analisi Giocatori")
    plot_wgr_progression(filtered_df)
    plot_player_rounds(filtered_df)

with tab8:
    st.subheader("🌐 Analisi Nazioni / Piattaforme")
    plot_top_nations(filtered_df)
    plot_platform_scores(filtered_df)

# --- FOOTER ---
st.caption("TGC Tours 2025 | Dashboard Pro v3 creata con ❤️ usando Streamlit & Plotly")

