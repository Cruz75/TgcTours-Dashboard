import requests
from bs4 import BeautifulSoup
import pandas as pd
from sqlalchemy import create_engine
import time

# 🔐 Inserisci la tua connection string Supabase qui
SUPABASE_CONNECTION_STRING = "postgresql://..."

GROUPS = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 19,
    "G": 20, "H": 22, "I": 23, "J": 24, "K": 25, "L": 26
}

SEASON = 2025

def get_existing_tournament_ids(engine):
    try:
        df = pd.read_sql("SELECT id FROM tournaments", engine)
        return set(df['id'].tolist())
    except:
        return set()

def get_tournaments(group_id):
    url = f"https://www.tgctours.com/Tour/Tournaments?tourId={group_id}&season={SEASON}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")

    tournaments = []
    for row in rows:
        try:
            cols = row.find_all("td")
            week = int(cols[0].text.strip())
            dates = cols[1].text.strip()
            name = cols[2].text.strip()
            course = cols[3].text.strip()
            purse = int(cols[4].text.strip().replace("$", "").replace(",", ""))
            champion = cols[5].text.strip()
            link = cols[6].find("a")["href"]
            tournament_id = int(link.split("/")[3].split("?")[0])
            tournaments.append({
                "id": tournament_id, "week": week, "dates": dates,
                "tournament_name": name, "course": course,
                "purse": purse, "champion": champion
            })
        except:
            continue
    return tournaments

def get_leaderboard(tournament_id, group_letter):
    url = f"https://www.tgctours.com/Tournament/Leaderboard/{tournament_id}?showEarnings=True"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")

    players = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 12:
            try:
                nation_tag = cols[1].find("span")
                nationality = nation_tag["title"] if nation_tag else None

                player_link = cols[2].find("a")
                raw_name = player_link["title"] if player_link else ""
                platform = raw_name.split(" - ")[0] if " - " in raw_name else None
                player = player_link.text.strip()

                scores = [int(c.text.strip()) if c.text.strip().isdigit() else None for c in cols[4:8]]
                strokes = int(cols[8].text.strip()) if cols[8].text.strip().isdigit() else None
                overunder = cols[3].text.strip()
                total = int(overunder) if overunder.replace("-", "").isdigit() else None

                earnings_raw = cols[10].text.strip().replace("$", "").replace(",", "")
                earnings = int(earnings_raw) if earnings_raw.isdigit() else 0

                promotion = cols[12].text.strip() or None

                players.append({
                    "player": player,
                    "group": group_letter,
                    "nationality": nationality,
                    "platform": platform,
                    "tournament_id": tournament_id,
                    "r1": scores[0], "r2": scores[1], "r3": scores[2], "r4": scores[3],
                    "strokes": strokes, "total": total,
                    "earnings": earnings, "promotion": promotion
                })
            except:
                continue
    return players

def main():
    engine = create_engine(SUPABASE_CONNECTION_STRING)
    existing_ids = get_existing_tournament_ids(engine)

    all_tournaments = []
    all_leaderboards = []

    for group_letter, group_id in GROUPS.items():
        tournaments = get_tournaments(group_id)
        new_tournaments = [t for t in tournaments if t["id"] not in existing_ids]
        all_tournaments.extend(new_tournaments)
        print(f"🆕 Gruppo {group_letter} → {len(new_tournaments)} nuovi tornei.")
        for t in new_tournaments:
            leaderboard = get_leaderboard(t["id"], group_letter)
            all_leaderboards.extend(leaderboard)
            print(f"  ↳ {t['tournament_name']} → {len(leaderboard)} giocatori.")
            time.sleep(0.5)

    if all_tournaments:
        df_tour = pd.DataFrame(all_tournaments)
        df_lead = pd.DataFrame(all_leaderboards)
        df_tour.to_sql("tournaments", engine, if_exists="append", index=False)
        df_lead.to_sql("leaderboards", engine, if_exists="append", index=False)
        print("✅ Dati nuovi inseriti.")
    else:
        print("⏸ Nessun nuovo torneo trovato.")

if __name__ == "__main__":
    main()
