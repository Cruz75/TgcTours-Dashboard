
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import requests
from bs4 import BeautifulSoup
import time

DB_URL = st.secrets["connection_string"]
engine = create_engine(DB_URL)

st.set_page_config(page_title="TGC Tours Dashboard", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            float: right;
        }
        .dataframe tbody tr th:only-of-type {
            vertical-align: middle;
        }
        .dataframe tbody tr th {
            vertical-align: top;
        }
        .dataframe thead th {
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    query = """
    SELECT l.*, t.week, t.dates, t.tournament_name, t.course, t.purse
    FROM leaderboards l
    JOIN tournaments t ON l.tournament_id = t.id
    """
    return pd.read_sql(query, engine)

def extract_promotions(tournament_id):
    url = f"https://www.tgctours.com/Tournament/Leaderboard/{tournament_id}?showEarnings=True"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")
    promos = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 12:
            player_tag = cols[2].find("a")
            if not player_tag:
                continue
            player_name = player_tag.text.strip()
            marks_cell = cols[11]
            icons = marks_cell.find_all("i")
            marks = []
            for icon in icons:
                cls = icon.get("class", [])
                if "fe-icon-arrow-up-circle" in cls:
                    marks.append("+1")
                elif "fe-icon-arrow-down-circle" in cls:
                    marks.append("-1")
                elif "fe-icon-award" in cls:
                    marks.append("winner")
                elif "fa" in cls and "fa-bolt" in cls:
                    marks.append("fast_track")
            if marks:
                promos.append((tournament_id, player_name, ",".join(marks)))
    return promos

def update_promotions():
    query = "SELECT DISTINCT tournament_id FROM leaderboards"
    existing_ids = pd.read_sql(query, engine)["tournament_id"].tolist()
    total_updated = 0
    for tid in existing_ids:
        promotions = extract_promotions(tid)
        with engine.begin() as conn:
            for tournament_id, player_name, promo_str in promotions:
                conn.execute(text("""
                    UPDATE leaderboards
                    SET promotion = :promotion
                    WHERE player = :player AND tournament_id = :tid
                """), {
                    "promotion": promo_str,
                    "player": player_name,
                    "tid": tournament_id
                })
        total_updated += len(promotions)
        time.sleep(0.3)
    return total_updated


# 🔄 Funzione per aggiornare tornei e dati leaderboard
def aggiorna_tutto():
    import scraper_update_fixed
    scraper_update_fixed.main()

if st.button("🔄 Aggiorna database tornei"):
    with st.spinner("Aggiornamento dei tornei e dei dati in corso..."):
        try:
            aggiorna_tutto()
            st.success("✅ Dati aggiornati con successo!")
        except Exception as e:
            st.error(f"Errore durante l'aggiornamento: {e}")


df = load_data()


# Estrazione date per calendario e filtro data
df["start_date"], df["end_date"] = zip(*df["dates"].apply(estrai_date_range))
df["start_date"] = pd.to_datetime(df["start_date"]).dt.date
df["end_date"] = pd.to_datetime(df["end_date"]).dt.date



from streamlit_calendar import calendar
import json

# Prepara eventi da mostrare nel calendario
eventi = []
for row in df[["tournament_name", "start_date", "end_date"]].drop_duplicates().itertuples():
    eventi.append({
        "title": row.tournament_name,
        "start": row.start_date.isoformat(),
        "end": (row.end_date + pd.Timedelta(days=1)).isoformat(),  # FullCalendar è end-exclusive
        "allDay": True
    })

calendar_config = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek"
    },
    "events": eventi,
    "editable": False,
    "selectable": False,
    "height": 600
}

st.markdown("### 📅 Tornei evidenziati nel calendario")
calendar(events=eventi, options=calendar_config)



# 📅 Selezione opzionale per data
@st.cache_data
def estrai_date_range(date_str):
    try:
        start, end = date_str.split(" - ")
        start = pd.to_datetime(start, format="%m/%d")
        end = pd.to_datetime(end, format="%m/%d")
        return start.replace(year=2025), end.replace(year=2025)
    except:
        return None, None

df["start_date"], df["end_date"] = zip(*df["dates"].apply(estrai_date_range))

usa_data = st.checkbox("📅 Filtra tornei per data", value=False)

if usa_data:
    min_data = df["start_date"].min()
    max_data = df["end_date"].max()
    selezione = st.date_input("Seleziona una data", value=min_data, min_value=min_data, max_value=max_data)
    tornei_attivi = df[(df["start_date"] <= selezione) & (df["end_date"] >= selezione)]
    if not tornei_attivi.empty:
        df = tornei_attivi.copy()
        st.markdown("### Tornei attivi nella data selezionata:")
        for torneo in tornei_attivi["tournament_name"].unique():
            st.markdown(f"- {torneo}")
    else:
        st.info("Nessun torneo attivo in questa data.")
else:
    st.markdown("### Visualizzazione completa senza filtro per data")


group_options = ["Tutti"] + sorted(df["group"].unique())
selected_group = st.sidebar.selectbox("Filtro gruppo", group_options)
if selected_group != "Tutti":
    df = df[df["group"] == selected_group]

# ➕ Filtri per piattaforma e nazionalità
platform_options = ["Tutti"] + sorted(df["platform"].dropna().unique())
selected_platform = st.sidebar.selectbox("Filtro piattaforma", platform_options)
if selected_platform != "Tutti":
    df = df[df["platform"] == selected_platform]

nation_options = ["Tutti"] + sorted(df["nationality"].dropna().unique())
selected_nation = st.sidebar.selectbox("Filtro nazionalità", nation_options)
if selected_nation != "Tutti":
    df = df[df["nationality"] == selected_nation]

df["torneo_label"] = df["week"].astype(str).str.zfill(2) + " - " + df["tournament_name"] + " (" + df["dates"] + ")"
tornei_unici = sorted(df["torneo_label"].unique())
selected_tournament = st.sidebar.radio("Seleziona torneo", tornei_unici)
df = df[df["torneo_label"] == selected_tournament]

# 🎯 Filtri selezionati
st.markdown(f"**Torneo selezionato:** `{selected_tournament}`")
st.markdown(f"**Gruppo:** `{selected_group}` | **Piattaforma:** `{selected_platform}` | **Nazionalità:** `{selected_nation}`")


df["completo"] = df[["r1", "r2", "r3", "r4"]].notnull().all(axis=1)
df["posizione"] = None
completi = df[df["completo"]].copy()
completi["posizione"] = completi["strokes"].rank(method="min").astype(int)
incompleti = df[~df["completo"]].copy()
incompleti["posizione"] = None
df = pd.concat([completi, incompleti])
df = df.sort_values(by=["completo", "posizione"], ascending=[False, True])

df["earnings"] = df["earnings"].apply(lambda x: f"${x:,}" if pd.notnull(x) and x != "" else "")
df["purse"] = df["purse"].apply(lambda x: f"${x:,}" if pd.notnull(x) else "")

def promotion_to_icons(promo):
    if not promo or pd.isna(promo):
        return ""
    icons = []
    for mark in promo.split(","):
        if mark == "+1":
            icons.append("🟢")
        elif mark == "-1":
            icons.append("🔴")
        elif mark == "winner":
            icons.append("🏆")
        elif mark == "fast_track":
            icons.append("⚡")
    return " ".join(icons)

df["promotion"] = df["promotion"].apply(promotion_to_icons)


st.title("🏌️‍♂️ TGC Tours Dashboard 2025")
st.markdown("Analisi completa dei tornei ufficiali su PGA Tour 2K25. Filtra per gruppo, torneo, piattaforma e nazionalità.")
st.markdown("---")

columns_to_show = [
    "posizione", "player", "group", "nationality", "platform",
    "r1", "r2", "r3", "r4", "strokes", "total", "earnings", "promotion",
    "tournament_name", "course", "purse", "dates"
]
st.dataframe(
    df[columns_to_show].reset_index(drop=True),
    height=700,
    use_container_width=True
)
