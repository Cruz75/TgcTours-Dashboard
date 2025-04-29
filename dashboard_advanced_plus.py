import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import plotly.express as px

# --- Configurazione Streamlit ---
st.set_page_config(page_title="TGC Tours Dashboard Plus", layout="wide")

st.title("🏌️‍♂️ TGC Tours - Dashboard Plus 2025")

# --- Connessione al database ---
connection_string = st.secrets["connection_string"]
engine = create_engine(connection_string)

# --- Caricamento dati ---
@st.cache_data(ttl=300)
def load_data():
    query = "SELECT * FROM leaderboards"
    df = pd.read_sql(query, engine)
    return df

# Pulsante Aggiorna Dati
if st.button("🔄 Aggiorna dati dal database"):
    st.cache_data.clear()
    st.rerun()

# Carica i dati
df = load_data()

# --- Sidebar: filtri dinamici ---
st.sidebar.header("🔎 Filtri Dati")
tournament_filter = st.sidebar.multiselect("Torneo", sorted(df['tournament_name'].unique()))
platform_filter = st.sidebar.multiselect("Piattaforma", sorted(df['platform'].dropna().unique()))
nationality_filter = st.sidebar.multiselect("Nazionalità", sorted(df['nationality'].dropna().unique()))
week_filter = st.sidebar.multiselect("Settimana", sorted(df['week'].dropna().unique()))

# Applica i filtri
filtered_df = df.copy()
if tournament_filter:
    filtered_df = filtered_df[filtered_df['tournament_name'].isin(tournament_filter)]
if platform_filter:
    filtered_df = filtered_df[filtered_df['platform'].isin(platform_filter)]
if nationality_filter:
    filtered_df = filtered_df[filtered_df['nationality'].isin(nationality_filter)]
if week_filter:
    filtered_df = filtered_df[filtered_df['week'].isin(week_filter)]

# --- Layout a Schede ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏆 Leaderboard", "📈 Punteggi", "🌍 Distribuzioni", "📅 Timeline Tornei", "🎯 Analisi WGR", "🏆 Top 10 + Best Round"])

# --- Tab 1: Leaderboard Completa ---
with tab1:
    st.subheader("🏆 Leaderboard Completa")
    st.dataframe(filtered_df, use_container_width=True)

# --- Tab 2: Grafici Punteggi ---
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

# --- Tab 3: Distribuzioni Piattaforme / Nazionalità ---
with tab3:
    st.subheader("🌍 Distribuzioni Piattaforme e Nazionalità")
    col1, col2 = st.columns(2)

    with col1:
        fig_platform = px.pie(filtered_df, names="platform", title="Distribuzione Giocatori per Piattaforma")
        st.plotly_chart(fig_platform, use_container_width=True)

    with col2:
        fig_nationality = px.pie(filtered_df, names="nationality", title="Distribuzione Giocatori per Nazionalità")
        st.plotly_chart(fig_nationality, use_container_width=True)

# --- Tab 4: Timeline Tornei ---
with tab4:
    st.subheader("📅 Andamento Totale Punteggi nel Tempo")
    if 'dates' in filtered_df.columns and 'total' in filtered_df.columns:
        timeline_df = filtered_df.groupby('dates')['total'].mean().reset_index()
        fig_timeline = px.line(timeline_df, x="dates", y="total", title="Media Totale Punteggi per Data Torneo")
        st.plotly_chart(fig_timeline, use_container_width=True)

# --- Tab 5: Analisi WGR ---
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

# --- Tab 6: Top 10 Giocatori e Best Round ---
with tab6:
    st.subheader("🏆 Top 10 Migliori Giocatori (Punteggio più basso)")

    top10 = filtered_df[['player', 'platform', 'total', 'tournament_name']].sort_values(by='total').head(10)
    st.dataframe(top10, use_container_width=True)

    st.subheader("🏅 Best Round Assoluto (Miglior punteggio singolo)")

    best_rounds = pd.melt(
        filtered_df,
        id_vars=["player", "platform", "tournament_name"],
        value_vars=["r1", "r2", "r3", "r4"],
        var_name="round",
        value_name="score"
    ).sort_values(by="score").dropna().head(10)

    st.dataframe(best_rounds, use_container_width=True)

# --- Footer ---
st.caption("TGC Tours 2025 | Dashboard Plus creata con ❤️ usando Streamlit e Plotly 🚀")
