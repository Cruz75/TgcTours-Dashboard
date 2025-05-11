import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# 📌 Metti qui la tua connection string Supabase
SUPABASE_CONNECTION_STRING = "postgresql://postgres.eqxbysuhuvmuxkowzzzi:#R!Pr_#%J6)briX@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

GROUPS = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 19,
    "G": 20, "H": 22, "I": 23, "J": 24, "K": 25, "L": 26
}
SEASON = 2025

def get_existing_tournament_ids(engine):
    df = pd.read_sql("SELECT id FROM tournaments", engine)
    return set(df["id"].tolist())

def get_tournaments(group_id):
    url = f"https://www.tgctours.com/Tour/Tournaments?tourId={group_id}&season={SEASON}"
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")

    tournaments = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue
        try:
            week = int(cols[0].text.strip())
            dates = cols[1].text.strip()
            name = cols[2].text.strip()
            course = cols[3].text.strip()
            purse = int(cols[4].text.strip().replace("$", "").replace(",", ""))
            champion = cols[5].text.strip()
            link = cols[6].find("a")["href"]
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
    url = f"https://www.tgctours.com/Tournament/Leaderboard/{tournament_id}?showEarnings=True"
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    rows = soup.find_all("tr")

    players = []
    for row in rows:
        cols = row.find_all("td")
        # riga di un giocatore ha almeno 12 colonne
        if len(cols) < 12:
            continue
        try:
            # nationality
            nation_tag = cols[1].find("span")
            nationality = nation_tag["title"] if nation_tag else None
            # player + platform
            player_link = cols[2].find("a")
            raw_title = player_link["title"] if player_link else ""
            if " - " in raw_title:
                platform, _ = map(str.strip, raw_title.split(" - ", 1))
            else:
                platform = None
            player = player_link.text.strip()
            # scores R1–R4
            scores = []
            for c in cols[4:8]:
                txt = c.text.strip()
                scores.append(int(txt) if txt.isdigit() else None)
            # strokes
            strokes_txt = cols[8].text.strip()
            strokes = int(strokes_txt) if strokes_txt.isdigit() else None
            # over/under → total
            ou_txt = cols[3].text.strip()
            total = int(ou_txt) if ou_txt.replace("-", "").isdigit() else None
            # earnings
            earn_txt = cols[10].text.strip().replace("$", "").replace(",", "")
            earnings = int(earn_txt) if earn_txt.isdigit() else 0
            # promotion marks
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
                "r1": scores[0], "r2": scores[1],
                "r3": scores[2], "r4": scores[3],
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
    Se hai già righe in leaderboards senza promotion, 
    questo ciclo aggiorna retroattivamente i marks.
    """
    existing_ids = pd.read_sql(
        "SELECT DISTINCT tournament_id FROM leaderboards", engine
    )["tournament_id"].tolist()

    for tid in existing_ids:
        promos = []
        # riusiamo extraction su singolo torneo
        lb = get_leaderboard(tid, group_letter=None)
        for rec in lb:
            if rec["promotion"]:
                promos.append((tid, rec["player"], rec["promotion"]))
        # UPDATE batch
        with engine.begin() as conn:
            for tournament_id, player_name, promo_str in promos:
                conn.execute(text("""
                    UPDATE leaderboards
                       SET promotion = :promo
                     WHERE tournament_id = :tid
                       AND player = :player
                """), {"promo": promo_str, "tid": tournament_id, "player": player_name})
                )
        time.sleep(0.2)

def main():
    engine = create_engine(SUPABASE_CONNECTION_STRING)
    existing_ids = get_existing_tournament_ids(engine)

    all_tournaments = []
    all_leaderboards = []

    for group_letter, group_id in GROUPS.items():
        # scarica tornei e filtri nuove entry
        tournaments = get_tournaments(group_id)
        new_tours = [t for t in tournaments if t["id"] not in existing_ids]
        all_tournaments.extend(new_tours)
        print(f"🆕 Gruppo {group_letter}: {len(new_tours)} nuovi tornei")
        # per ciascun torneo, scarica leaderboard completa (con promotion)
        for t in new_tours:
            lb = get_leaderboard(t["id"], group_letter)
            all_leaderboards.extend(lb)
            print(f"  ↳ {t['tournament_name']} → {len(lb)} giocatori")
            time.sleep(0.5)

    # salvo nuovi dati
    if all_tournaments:
        df_t = pd.DataFrame(all_tournaments)
        df_lb = pd.DataFrame(all_leaderboards)
        df_t.to_sql("tournaments", engine, if_exists="append", index=False)
        df_lb.to_sql("leaderboards", engine, if_exists="append", index=False)
        print("✅ Tornei e leaderboard nuove inseriti.")

        # opzionale: aggiorna tutte le promotion (inclusi vecchi record)
        update_all_promotions(engine)
        print("✅ Promotion marks aggiornati su tutti i record.")
    else:
        print("⏸ Nessun nuovo torneo trovato.")

if __name__ == "__main__":
    main()
