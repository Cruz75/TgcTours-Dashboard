# update_promotions.py

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

# 1) Leggi la connessione da env var
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Devi esportare DATABASE_URL prima di eseguire questo script")

engine = create_engine(DATABASE_URL)

def fetch_promotion_marks(tid: int):
    """
    Scarica la leaderboard del torneo e restituisce
    una lista di tuple: (player_name, promo_str)
    """
    url = f"https://www.tgctours.com/Tournament/Leaderboard/{tid}?showEarnings=True"
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    marks = []
    # seleziona solo le righe con giocatori (escludi taglio e intestazioni)
    for tr in soup.select("table.leaderboard tbody tr"):
        # skip rows with colspan (cut line, etc)
        if tr.find("td", {"colspan": True}):
            continue

        # estrai nome
        name_td = tr.find("td", {"data-title": "Player"})
        if not name_td:
            continue
        player_name = name_td.get_text(strip=True)

        # estrai le icone dalla colonna Marks / promotion
        promo_td = tr.find("td", {"data-title": "Marks"})
        if not promo_td:
            continue
        icons = promo_td.find_all("i")
        promo_list = []
        for ic in icons:
            cls = ic.get("class", [])
            if "fe-icon-arrow-up-circle" in cls:
                promo_list.append("+1")
            elif "fe-icon-arrow-down-circle" in cls:
                promo_list.append("-1")
            elif "fe-icon-award" in cls:
                promo_list.append("winner")
            elif "fa-bolt" in cls:
                promo_list.append("fast_track")
        promo_str = ",".join(promo_list)
        marks.append((player_name, promo_str))
    return marks

def update_all_promotions():
    # 2) prendi tutti i tournament_id in leaderboards
    df_ids = pd.read_sql("SELECT DISTINCT tournament_id FROM leaderboards", engine)
    total = 0

    for tid in df_ids["tournament_id"]:
        promos = fetch_promotion_marks(tid)
        if not promos:
            continue

        with engine.begin() as conn:
            for player_name, promo_str in promos:
                # 3) aggiorna row per row
                res = conn.execute(
                    text("""
                        UPDATE leaderboards
                           SET promotion = :promo
                         WHERE tournament_id = :tid
                           AND player = :player
                    """),
                    {"promo": promo_str, "tid": tid, "player": player_name}
                )
                total += res.rowcount

        print(f"✔️  Tourn. {tid}: aggiornate {len(promos)} promozioni")
        time.sleep(0.2)

    print(f"\n🎯 Totale record aggiornati: {total}")

if __name__ == "__main__":
    update_all_promotions()
