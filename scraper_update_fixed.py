import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# 📌 Sostituisci con la tua connection string Supabase
SUPABASE_CONNECTION_STRING = "postgresql://postgres.eqxbysuhuvmuxkowzzzi:#R!Pr_#%J6)briX@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

# Mappatura gruppi → tourId
GROUPS = {
    "A": 10, "B": 11, "C": 12, "D": 13,
    "E": 14, "F": 19, "G": 20, "H": 22,
    "I": 23, "J": 24, "K": 25, "L": 26
}
SEASON = 2025

def get_existing_tournament_ids(engine):
    df = pd.read_sql("SELECT id FROM tournaments", engine)
    return set(df["id"].tolist())

def get_tournaments(group_id):
    url = f"https://www.tgctours.com/Tour/Tournaments?tourId={group_id}&season={SEASON}"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tournaments = []
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) < 6:
            continue
        try:
            week = int(cols[0].text.strip())
            dates = cols[1].text.strip()
            name = cols[2].text.strip()
            course = cols[3].text.strip()
            purse = int(
                cols[4].text.strip()
                .replace("$", "")
                .replace(",", "")
            )
            champion = cols[5].text.strip()
            link = cols[6].find("a")["href"]
            # es: "/Tournament/Leaderboard/8900?showEarnings=True"
            tournament_id = int(link.split("/")[3].split("?")[0])
            tournaments.append({
                "id": tournament_id,
                "week": week,
                "dates": dates,
                "tournament_name": name,
                "course": course,
                "purse": purse,
                "champion": champion
            })
        except Exception:
            continue

    return tournaments

def get_leaderboard(tournament_id, group_letter):
    url = (
        f"https://www.tgctours.com/Tournament/Leaderboard/"
        f"{tournament_id}?showEarnings=True"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    players = []
    for row in soup.select("table.leaderboard tbody tr"):
        cols = row.find_all("td")
        # Escludi righe di taglio o intestazione
        if len(cols) < 12 or row.find("td", {"colspan": True}):
            continue
        try:
            # Nazionalità
            nation_tag = cols[1].find("span")
            nationality = nation_tag["title"] if nation_tag else None
            # Player + piattaforma nel title
            player_link = cols[2].find("a")
            raw_title = player_link.get("title", "") if player_link else ""
            if " - " in raw_title:
                platform, _ = raw_title.split(" - ", 1)
                platform = platform.strip()
            else:
                platform = None
            player = player_link.text.strip() if player_link else None
            # Punteggi R1–R4
            scores = []
            for c in cols[4:8]:
                txt = c.text.strip()
                scores.append(int(txt) if txt.isdigit() else None)
            # Strokes (colpi totali)
            strokes_txt = cols[8].text.strip()
            strokes = int(strokes_txt) if strokes_txt.isdigit() else None
            # Total (over/under) se presente
            ou_txt = cols[3].text.strip()
            total = int(ou_txt) if ou_txt.replace("-", "").isdigit() else None
            # Earnings
            earn_txt = cols[10].text.strip().replace("$", "").replace(",", "")
            earnings = int(earn_txt) if earn_txt.isdigit() else 0
            # Promotion marks
            marks_cell = cols[11]
            icons = marks_cell.find_all("i")
            promo = []
            for ic in icons:
                cls = ic.get("class", [])
                if "fe-icon-arrow-up-circle" in cls:
                    promo.append("+1")
                elif "fe-icon-arrow-down-circle" in cls:
                    promo.append("-1")
                elif "fe-icon-award" in cls:
                    promo.append("winner")
                elif "fa-bolt" in cls:
                    promo.append("fast_track")
            promo_str = ",".join(promo) if promo else ""

            players.append({
                "player": player,
                "group": group_letter,
                "nationality": nationality,
                "platform": platform,
                "tournament_id": tournament_id,
                "r1": scores[0],
                "r2": scores[1],
                "r3": scores[2],
                "r4": scores[3],
                "strokes": strokes,
                "total": total,
                "earnings": earnings,
                "promotion": promo_str
            })
        except Exception:
            continue

    return players

def update_all_promotions(engine):
    """
    Aggiorna retroattivamente tutte le righe esistenti in leaderboards
    con i promotion marks corretti.
    """
    df_ids = pd.read_sql(
        "SELECT DISTINCT tournament_id FROM leaderboards", engine
    )
    for tid in df_ids["tournament_id"].tolist():
        lb_recs = get_leaderboard(tid, group_letter=None)
        with engine.begin() as conn:
            for rec in lb_recs:
                promo = rec.get("promotion", "")
                if promo:
                    conn.execute(
                        text(
                            "UPDATE leaderboards "
                            "SET promotion = :promo "
                            "WHERE tournament_id = :tid "
                            "AND player = :player"
                        ),
                        {"promo": promo, "tid": tid, "player": rec["player"]}
                    )
        time.sleep(0.2)

def main():
    engine = create_engine(SUPABASE_CONNECTION_STRING)
    existing_ids = get_existing_tournament_ids(engine)

    new_tournaments = []
    new_leaderboards = []

    for group_letter, group_id in GROUPS.items():
        tours = get_tournaments(group_id)
        fresh = [t for t in tours if t["id"] not in existing_ids]
        new_tournaments.extend(fresh)
        print(f"Gruppo {group_letter}: trovati {len(fresh)} nuovi tornei")
        for t in fresh:
            lb = get_leaderboard(t["id"], group_letter)
            new_leaderboards.extend(lb)
            print(f"  → {t['tournament_name']}: {len(lb)} giocatori")
            time.sleep(0.5)

    if new_tournaments:
        df_t = pd.DataFrame(new_tournaments)
        df_lb = pd.DataFrame(new_leaderboards)
        df_t.to_sql("tournaments", engine, if_exists="append", index=False)
        df_lb.to_sql("leaderboards", engine, if_exists="append", index=False)
        print("✅ Nuovi tornei e leaderboard inseriti")
        update_all_promotions(engine)
        print("✅ Promotion marks aggiornati su tutte le righe")
    else:
        print("ℹ️ Nessun nuovo torneo da aggiornare")

if __name__ == "__main__":
    main()
