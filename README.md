# TGC Tours Dashboard

Questa dashboard mostra e analizza i risultati dei tornei PGA Tour 2K25 su [TGC Tours](https://www.tgctours.com), permettendo di filtrare per gruppo, torneo, piattaforma e nazionalità, con aggiornamenti automatici del database.

## 🚀 Funzionalità principali

- Visualizzazione classifiche torneo per torneo
- Filtri per gruppo, piattaforma e nazionalità
- Simboli per promozioni, retrocessioni, vittorie e fast-track
- Aggiornamento automatico dei dati da TGC Tours via scraper

## 🧩 Requisiti

Assicurati di avere nel tuo `requirements.txt`:
```
streamlit
pandas
sqlalchemy
psycopg2-binary
requests
beautifulsoup4
```

## 🗂️ Struttura del progetto

```
📁 project-root
├── dashboard_advanced_plus.py
├── scraper_update_fixed.py
├── requirements.txt
└── .streamlit/
    └── secrets.toml
```

## 🔐 secrets.toml (non nel repo)

Crea un file `.streamlit/secrets.toml` **solo in locale** o nella sezione **Secrets** di [Streamlit Cloud](https://streamlit.io/cloud):

```toml
connection_string = "postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE"
login_username = "admin"
login_password = "tigercruz"
```

## 🖥️ Avvio locale

```bash
streamlit run dashboard_ricostruita.py
```

## ☁️ Deployment

1. Pubblica su GitHub.
2. Collega il repo a [Streamlit Cloud](https://streamlit.io/cloud).
3. Imposta i secrets nella dashboard di gestione.

## 🧩 Aggiornamento Dati

Clicca sul pulsante **"🔄 Aggiorna database tornei"** per estrarre gli ultimi risultati disponibili su TGC Tours. Il sistema aggiornerà automaticamente i tornei e i leaderboard nel database.

---

Creato con ❤️ per l’analisi dei dati nel golf competitivo online.
