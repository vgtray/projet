# Trade Bot

Bot de trading automatisé basé sur la stratégie SMC/ICT (Smart Money Concepts), opérant sur **XAUUSD** et **NAS100** en timeframe M5.

## Stack

- **Python** — Langage principal
- **MetaTrader 5** — Exécution des ordres via mt5linux (RPyC)
- **Groq / Llama 3.3 70B** — Analyse IA des setups
- **PostgreSQL** — Persistance des signaux, trades et performances

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
```

Renseigner les clés API dans `.env` avant de lancer le bot.

## Lancement

```bash
python main.py
```
