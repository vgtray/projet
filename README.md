# 🤖 Trade Bot SMC/ICT

**Bot de trading automatisé basé sur la stratégie Smart Money Concepts / ICT**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![MetaTrader 5](https://img.shields.io/badge/MT5-Docker%20RPyC-blue)](https://www.metatrader5.com)
[![MiniMax](https://img.shields.io/badge/LLM-MiniMax%20M2.5-orange)](https://api.minimax.io)

> Trading algorithmique sur **XAUUSD** (Or) et **US100** (Nasdaq) en timeframe M5, exclusivement pendant la session New York (14h30–21h00 Paris). Le bot utilise MiniMax M2.5 comme cerveau décisionnel avec fallback automatique sur Groq Llama 3.3 70B.

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────┐
│              Dashboard Next.js (:3000)               │
│  ├─ Live trades / PnL en temps réel                  │
│  ├─ Logs agent avec auto-refresh                     │
│  ├─ Status des sources de données                    │
│  └─ Override manuel (pause/resume, fermeture trade)  │
└──────────────────┬───────────────────────────────────┘
                   │ API Routes (PostgreSQL)
┌──────────────────▼───────────────────────────────────┐
│              Bot Python (main.py)                     │
│  ┌─────────────────────────────────────────────────┐ │
│  │  MiniMax M2.5 API (cerveau principal)           │ │
│  │  → Tool use natif, décisions agentic            │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Groq Llama 3.3 70B (fallback automatique)      │ │
│  │  → Si MiniMax timeout (>10s) ou indisponible    │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────┐ │
│  │  Sources de données                             │ │
│  │  ├── MT5 RPyC (prix live OHLCV M5)             │ │
│  │  ├── NewsAPI (sentiment actualités)             │ │
│  │  ├── Reddit/PRAW (sentiment social)             │ │
│  │  └── Indicateurs (RSI, MACD, EMA 20/50/200)    │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│           PostgreSQL (trade)                          │
│  ├── signals        (décisions IA)                   │
│  ├── trades         (exécutions réelles)             │
│  ├── performance_stats (agrégats par pattern)        │
│  ├── daily_trade_counts (anti-overtrade)             │
│  └── bot_state      (persistance état)               │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│           MT5 Docker Container (OVH)                  │
│  └── localhost:8001 (RPyC)                            │
│      ├── XAUUSD  (M5, session NY)                    │
│      └── US100   (M5, session NY)                    │
│      Broker : Vantage International (demo)           │
└──────────────────────────────────────────────────────┘
```

---

## 🛠 Stack technique

| Composant | Technologie | Rôle |
|-----------|-------------|------|
| **Bot** | Python 3.10+ | Moteur de trading, analyse, exécution |
| **LLM principal** | MiniMax M2.5 (OpenAI SDK compatible) | Décisions de trading agentic |
| **LLM fallback** | Groq + Llama 3.3 70B | Relais automatique si MiniMax indisponible |
| **Dashboard** | Next.js 16 + React 19 + Tailwind CSS 4 | Monitoring temps réel |
| **Base de données** | PostgreSQL 14+ | Persistance signaux, trades, état |
| **Broker** | MetaTrader 5 via Docker RPyC (mt5linux) | Exécution des ordres |
| **Indicateurs** | ta, pandas, numpy | RSI, MACD, EMA 20/50/200 |
| **News** | NewsAPI | Sentiment actualités |
| **Social** | Reddit (PRAW) | Sentiment r/Forex, r/Gold, r/investing, r/stocks |
| **Graphiques** | Recharts | Visualisation PnL dans le dashboard |
| **VPS** | OVH 31 GB RAM, 8 cores, Ubuntu/Debian | Hébergement production |

---

## ⚡ Fonctionnalités

### Bot Python

- Analyse automatique à chaque nouvelle bougie M5 fermée
- Détection algorithmique des confluences (FVG, OB, iFVG, Breaker Block)
- Calcul dynamique des niveaux clés (Asia, London, Previous Day)
- Routing LLM intelligent : MiniMax → Groq fallback automatique
- Calcul du lot size dynamique (1% du capital, jamais de lot fixe)
- Anti-overtrade : max 2 trades/jour/asset, persisté en DB
- Déduplication des signaux sur fenêtre glissante de 15 minutes
- Monitoring des positions ouvertes toutes les 30 secondes
- Auto-calibration via injection des performances passées dans le prompt
- Dégradation gracieuse complète (aucun crash définitif)

### Dashboard Next.js

- Vue temps réel des trades ouverts et fermés
- Statistiques globales : win rate, PnL total, RR moyen
- Compteur journalier de trades par asset
- Historique des signaux IA avec filtrage (asset, validité)
- Lecteur de logs en direct
- Contrôle du bot : pause / resume
- Fermeture manuelle d'un trade depuis l'interface
- Performance par pattern de trading

---

## 📊 Stratégie de trading

### Smart Money Concepts / ICT

La stratégie repose sur le comportement institutionnel du marché : les « smart money » (banques, fonds) créent des mouvements de liquidation pour piéger les traders retail avant de lancer le vrai mouvement.

### 3 conditions obligatoires pour entrer en position

| # | Condition | Description |
|---|-----------|-------------|
| 1 | **Liquidity Sweep** | Un niveau clé (Asia/London/PrevDay High ou Low) a été dépassé |
| 2 | **Confluence** | Le prix revient dans une zone technique (FVG, OB, iFVG, BB) |
| 3 | **Confirmation** | Bougie de confirmation franche dans le sens du trade |

**Si une seule condition manque** → pas de trade.

### 2 scénarios de trading

| Scénario | Description | Cible |
|----------|-------------|-------|
| **Reversal** | Le marché dépasse un niveau puis repart en sens inverse. Les traders piégés ferment → on trade le retournement | Prochain high/low opposé |
| **Continuation** | Le marché dépasse un niveau et poursuit dans le même sens. Tendance forte, pas de reversal | Prochain high/low dans le sens du mouvement |

### Gestion du risque

- **Risque par trade** : 1% du capital
- **Stop Loss** : derrière le niveau dépassé (invalidation de l'idée)
- **Take Profit** : prochain key level visible (jamais de niveaux inventés)
- **Anti-overtrade** : max 2 trades/jour/asset, compteur persisté en DB
- **Déduplication** : même asset + direction + sweep_level dans les 15 dernières minutes → ignoré

---

## 📁 Structure du projet

```
projet/
├── main.py                    # Point d'entrée — lance les boucles d'analyse et monitoring
├── requirements.txt           # Dépendances Python
├── .env                       # Variables d'environnement (non commité)
├── .env.example               # Template des variables d'environnement
├── .gitignore                 # Fichiers exclus du versionning
├── SPEC.md                    # Spécification technique complète
│
├── src/                       # Code source du bot Python
│   ├── __init__.py            # Package marker
│   ├── config.py              # Configuration centralisée (charge .env + constantes spec)
│   ├── bot.py                 # Logique principale du bot (boucle, orchestration)
│   ├── llm_client.py          # Client LLM : MiniMax (principal) + Groq (fallback)
│   ├── mt5_client.py          # Client MetaTrader 5 via RPyC (données + exécution)
│   ├── database.py            # Couche PostgreSQL (signals, trades, state, compteurs)
│   ├── key_levels.py          # Calcul niveaux clés (Asia/London/PrevDay High & Low)
│   ├── confluences.py         # Détection FVG, OB, iFVG, Breaker Block
│   ├── indicators.py          # Calcul RSI, MACD, EMA 20/50/200
│   ├── sentiment.py           # Sentiment NewsAPI + Reddit
│   └── logging_setup.py       # Configuration logging (rotation journalière, 30j)
│
├── sql/
│   └── init.sql               # Schéma PostgreSQL (idempotent, CREATE IF NOT EXISTS)
│
├── logs/                      # Logs du bot (rotation journalière, non commité)
│   └── bot.log
│
└── dashboard/                 # Dashboard Next.js de monitoring
    ├── package.json           # Dépendances Node.js
    ├── tsconfig.json          # Configuration TypeScript
    ├── next.config.ts         # Configuration Next.js
    ├── postcss.config.mjs     # Configuration PostCSS/Tailwind
    ├── eslint.config.mjs      # Configuration ESLint
    ├── .env.local             # Variables d'environnement dashboard (non commité)
    ├── public/                # Assets statiques
    └── src/
        ├── app/
        │   ├── layout.tsx     # Layout racine
        │   ├── page.tsx       # Page d'accueil (overview)
        │   ├── globals.css    # Styles globaux Tailwind
        │   ├── signals/
        │   │   └── page.tsx   # Page historique des signaux
        │   ├── logs/
        │   │   └── page.tsx   # Page lecteur de logs
        │   └── api/
        │       ├── signals/route.ts          # GET signaux avec filtrage
        │       ├── trades/route.ts           # GET trades (open/closed/all)
        │       ├── trades/[id]/close/route.ts # POST fermeture manuelle
        │       ├── stats/route.ts            # GET statistiques globales
        │       ├── status/route.ts           # GET état du bot
        │       ├── bot/route.ts              # POST pause/resume
        │       └── logs/route.ts             # GET dernières lignes de log
        ├── components/
        │   ├── Header.tsx     # En-tête navigation
        │   ├── BotStatus.tsx  # Indicateur état du bot
        │   ├── StatsBar.tsx   # Barre de statistiques
        │   ├── SignalRow.tsx   # Ligne signal dans le tableau
        │   ├── TradeRow.tsx   # Ligne trade dans le tableau
        │   ├── LogViewer.tsx  # Composant lecteur de logs
        │   └── ui/
        │       ├── Card.tsx   # Composant carte
        │       ├── Badge.tsx  # Composant badge
        │       └── Stat.tsx   # Composant statistique
        └── lib/
            ├── db.ts          # Pool de connexion PostgreSQL
            └── utils.ts       # Fonctions utilitaires (cn, formatage)
```

---

## 🚀 Installation & Setup

### Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Python | 3.10+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| MT5 Docker | Container RPyC sur le VPS, port 8001 |

### Bot Python

```bash
# 1. Cloner le projet
git clone <url-du-repo> projet
cd projet

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# 4. Initialiser la base de données
psql -d trade -f sql/init.sql

# 5. Lancer le bot
python main.py
```

### Dashboard Next.js

```bash
# 1. Aller dans le dossier dashboard
cd dashboard

# 2. Installer les dépendances
npm install

# 3. Configurer les variables d'environnement
cp .env.local.example .env.local
# Éditer avec les infos de connexion DB

# 4. Lancer en développement
npm run dev
# → http://localhost:3000

# 5. Build production
npm run build
npm run start
```

---

## ⚙️ Configuration

### Variables d'environnement du bot (.env)

| Variable | Obligatoire | Défaut | Description |
|----------|:-----------:|--------|-------------|
| `MINIMAX_API_KEY` | ✅ | — | Clé API MiniMax (LLM principal) |
| `MINIMAX_BASE_URL` | ❌ | `https://api.minimax.io/v1` | URL de base API MiniMax |
| `MINIMAX_MODEL` | ❌ | `MiniMax-M2.5` | Modèle MiniMax à utiliser |
| `LLM_TIMEOUT` | ❌ | `10` | Timeout LLM en secondes avant fallback |
| `GROQ_API_KEY` | ✅ | — | Clé API Groq (LLM fallback) |
| `GROQ_MODEL` | ❌ | `llama-3.3-70b-versatile` | Modèle Groq à utiliser |
| `NEWSAPI_KEY` | ✅ | — | Clé API NewsAPI |
| `REDDIT_CLIENT_ID` | ❌ | — | Client ID Reddit (optionnel) |
| `REDDIT_CLIENT_SECRET` | ❌ | — | Client Secret Reddit (optionnel) |
| `REDDIT_USER_AGENT` | ❌ | `trade_bot/1.0` | User Agent pour l'API Reddit |
| `DB_HOST` | ❌ | `localhost` | Hôte PostgreSQL |
| `DB_PORT` | ❌ | `5432` | Port PostgreSQL |
| `DB_NAME` | ❌ | `trade` | Nom de la base de données |
| `DB_USER` | ❌ | `adam` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | ✅ | — | Mot de passe PostgreSQL |
| `MT5_HOST` | ❌ | `localhost` | Hôte du container MT5 |
| `MT5_PORT` | ❌ | `8001` | Port RPyC du container MT5 |

### Variables d'environnement du dashboard (.env.local)

| Variable | Obligatoire | Défaut | Description |
|----------|:-----------:|--------|-------------|
| `DB_HOST` | ❌ | `localhost` | Hôte PostgreSQL |
| `DB_PORT` | ❌ | `5432` | Port PostgreSQL |
| `DB_NAME` | ❌ | `trade` | Nom de la base de données |
| `DB_USER` | ❌ | `adam` | Utilisateur PostgreSQL |
| `DB_PASSWORD` | ✅ | — | Mot de passe PostgreSQL |
| `LOG_PATH` | ❌ | `/Users/adam/Documents/projet/logs/bot.log` | Chemin vers le fichier de logs du bot |

---

## 🗄 Base de données

### Schéma des tables

Le script `sql/init.sql` est **idempotent** (`CREATE IF NOT EXISTS`) — il peut être exécuté plusieurs fois sans risque.

#### `signals` — Décisions IA

Chaque appel au LLM produit un enregistrement, qu'il débouche sur un trade ou non.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL PK | Identifiant unique |
| `asset` | VARCHAR(10) | XAUUSD ou US100 |
| `timestamp` | TIMESTAMPTZ | Horodatage de l'analyse |
| `direction` | VARCHAR(10) | long, short ou none |
| `scenario` | VARCHAR(20) | reversal, continuation, unclear ou none |
| `confidence` | INTEGER | Score de confiance 0–100 |
| `entry_price` | DECIMAL(12,5) | Prix d'entrée proposé |
| `sl_price` | DECIMAL(12,5) | Stop Loss proposé |
| `tp_price` | DECIMAL(12,5) | Take Profit proposé |
| `rr_ratio` | DECIMAL(5,2) | Ratio Risk/Reward |
| `confluences_used` | TEXT[] | Confluences détectées (FVG, OB, etc.) |
| `sweep_level` | VARCHAR(20) | Niveau clé dépassé |
| `news_sentiment` | VARCHAR(10) | bullish, bearish ou neutral |
| `social_sentiment` | VARCHAR(10) | bullish, bearish ou neutral |
| `trade_valid` | BOOLEAN | Signal exploitable ou non |
| `reason` | TEXT | Explication en français |
| `executed` | BOOLEAN | Trade réellement exécuté |
| `llm_used` | VARCHAR(20) | MiniMax ou Groq |
| `created_at` | TIMESTAMPTZ | Date de création |

#### `trades` — Exécutions réelles

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL PK | Identifiant unique |
| `signal_id` | INTEGER FK → signals | Signal ayant déclenché le trade |
| `asset` | VARCHAR(10) | XAUUSD ou US100 |
| `entry_time` | TIMESTAMPTZ | Heure d'entrée |
| `exit_time` | TIMESTAMPTZ | Heure de sortie (null si ouvert) |
| `direction` | VARCHAR(10) | long ou short |
| `entry_price` | DECIMAL(12,5) | Prix d'entrée réel |
| `exit_price` | DECIMAL(12,5) | Prix de sortie réel |
| `sl_price` | DECIMAL(12,5) | Stop Loss |
| `tp_price` | DECIMAL(12,5) | Take Profit |
| `lot_size` | DECIMAL(10,5) | Taille du lot (calculée dynamiquement) |
| `mt5_ticket` | BIGINT | Numéro de ticket MT5 |
| `pnl` | DECIMAL(10,2) | Profit/perte en devise |
| `status` | VARCHAR(20) | open, closed, etc. |
| `closed_reason` | VARCHAR(20) | tp, sl, manual, etc. |
| `created_at` | TIMESTAMPTZ | Date de création |

#### `performance_stats` — Agrégats par pattern

Utilisé pour l'auto-calibration : le bot injecte un résumé des performances passées similaires dans chaque prompt.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL PK | Identifiant unique |
| `pattern_type` | VARCHAR(50) | Type de pattern (ex: reversal_FVG_asia_high) |
| `asset` | VARCHAR(10) | XAUUSD ou US100 |
| `total_trades` | INTEGER | Nombre total de trades |
| `winning_trades` | INTEGER | Trades gagnants |
| `losing_trades` | INTEGER | Trades perdants |
| `win_rate` | DECIMAL(5,2) | Taux de réussite |
| `avg_rr` | DECIMAL(5,2) | RR moyen réalisé |
| `total_pnl` | DECIMAL(15,2) | PnL total |
| `last_updated` | TIMESTAMPTZ | Dernière mise à jour |

#### `daily_trade_counts` — Anti-overtrade

Compteur persisté pour éviter qu'un redémarrage du bot réinitialise le compteur à zéro.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL PK | Identifiant unique |
| `asset` | VARCHAR(10) | XAUUSD ou US100 |
| `trade_date` | DATE | Date du jour (Paris) |
| `closed_trades` | INTEGER | Nombre de trades fermés ce jour |

**Contrainte** : UNIQUE(asset, trade_date)

#### `bot_state` — Persistance état

Stocke l'état entre redémarrages : dernière bougie analysée, état pause/resume, demandes de fermeture manuelle.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | SERIAL PK | Identifiant unique |
| `key` | VARCHAR(50) UNIQUE | Clé d'état (ex: `last_analyzed_XAUUSD`) |
| `value` | TEXT | Valeur associée |
| `updated_at` | TIMESTAMPTZ | Dernière mise à jour |

---

## 🌐 API du Dashboard

### Endpoints

| Méthode | Path | Description |
|---------|------|-------------|
| `GET` | `/api/signals` | Liste des signaux IA |
| `GET` | `/api/trades` | Liste des trades |
| `POST` | `/api/trades/[id]/close` | Demande de fermeture manuelle d'un trade |
| `GET` | `/api/stats` | Statistiques globales et par pattern |
| `GET` | `/api/status` | État du bot (actif, en pause, dernière analyse) |
| `POST` | `/api/bot` | Contrôle du bot (pause / resume) |
| `GET` | `/api/logs` | Dernières lignes du fichier de logs |

### Détail des endpoints

#### `GET /api/signals`

**Paramètres query** : `limit` (max 200, défaut 20), `valid` (`true`/`false`), `asset` (`XAUUSD`/`US100`)

```json
{
  "signals": [
    {
      "id": 1,
      "asset": "XAUUSD",
      "direction": "short",
      "confidence": 75,
      "trade_valid": true,
      "reason": "Sweep asia_high confirmé avec FVG",
      "llm_used": "minimax",
      ...
    }
  ]
}
```

#### `GET /api/trades`

**Paramètres query** : `status` (`open`/`closed`/`all`), `limit` (max 200, défaut 50)

```json
{
  "trades": [
    {
      "id": 1,
      "asset": "XAUUSD",
      "direction": "short",
      "entry_price": 2045.50,
      "pnl": 12.30,
      "status": "closed",
      "closed_reason": "tp",
      ...
    }
  ]
}
```

#### `POST /api/trades/[id]/close`

Enregistre une demande de fermeture manuelle via `bot_state`. Le bot Python détecte cette demande et ferme la position sur MT5.

```json
{ "success": true, "trade_id": 42 }
```

#### `GET /api/stats`

```json
{
  "global": {
    "total_trades": 28,
    "winning_trades": 17,
    "losing_trades": 11,
    "total_pnl": 34.50,
    "win_rate": 60.7,
    "avg_rr": 1.85,
    "open_trades": 1
  },
  "today": { "XAUUSD": 1, "US100": 0 },
  "performance_by_pattern": [...]
}
```

#### `GET /api/status`

```json
{
  "bot_active": true,
  "bot_paused": false,
  "last_analyzed_XAUUSD": "2026-02-23T15:35:00Z",
  "last_analyzed_US100": "2026-02-23T15:35:00Z",
  "db_connected": true
}
```

#### `POST /api/bot`

**Body** : `{ "action": "pause" }` ou `{ "action": "resume" }`

```json
{ "success": true, "state": "paused" }
```

#### `GET /api/logs`

**Paramètres query** : `lines` (max 500, défaut 100)

```json
{
  "logs": [
    "2026-02-23 14:30:00 [INFO] New M5 candle detected for XAUUSD",
    "2026-02-23 14:30:01 [INFO] Signal: short | Valid: True | Confidence: 75%"
  ],
  "total": 1520,
  "returned": 100
}
```

---

## 🔄 Flux de traitement

### Boucle principale — toutes les 10 secondes

Le bot ne lance une analyse LLM que lorsqu'une **nouvelle bougie M5 est fermée** (pas d'analyse à intervalle fixe).

1. **Fetch** des dernières bougies MT5 pour chaque asset
2. **Compare** le timestamp avec la dernière bougie analysée (persisté en DB)
3. **Si nouvelle bougie** → suite du traitement, sinon → attente prochaine itération
4. **Calcul** des niveaux clés (Asia/London/PrevDay High & Low)
5. **Détection** algorithmique des confluences (FVG, OB, iFVG)
6. **Fetch** sentiment (NewsAPI + Reddit)
7. **Query** performances passées similaires (auto-calibration)
8. **Construction** du prompt avec tout le contexte
9. **Appel LLM** : MiniMax M2.5 → si timeout (>10s), fallback Groq Llama 3.3
10. **Parse** la réponse JSON stricte
11. **Sauvegarde** du signal en DB
12. **Vérification** anti-duplication (fenêtre 15 min)
13. **Exécution** sur MT5 si le signal est valide
14. **Mise à jour** du timestamp de dernière analyse

### Boucle monitoring — toutes les 30 secondes

1. **Fetch** des positions ouvertes sur MT5
2. **Détection** des TP/SL touchés
3. **Mise à jour** de la table `trades` (exit_price, pnl, status)
4. **Mise à jour** de la table `performance_stats`
5. **Incrémentation** du compteur journalier (`daily_trade_counts`)

### Routing LLM

| Priorité | Fournisseur | Condition |
|----------|-------------|-----------|
| 1 | **MiniMax M2.5** | Cerveau principal — meilleur en tâches agentic/tool use |
| 2 | **Groq Llama 3.3 70B** | Activé automatiquement si MiniMax timeout (>10s) ou indisponible |

> En mode fallback, `trade_valid` est forcé à `false` sauf si `confidence > 85`.

---

## 🛡 Gestion des erreurs

### Retry automatique

- **Tentatives** : 3 maximum
- **Backoff exponentiel** : 30s → 60s → 120s
- **Logging** : chaque tentative est tracée

### Dégradation gracieuse

| Service indisponible | Comportement | Impact trading |
|---------------------|--------------|----------------|
| **MiniMax API** | Switch automatique sur Groq | `trade_valid: false` sauf confidence > 85 |
| **Groq API** | `trade_valid: false`, reason: "llm_unavailable" | Aucun trade exécuté |
| **NewsAPI** | `news_sentiment: neutral` | Analyse continue sans news |
| **Reddit** | `social_sentiment: neutral` | Analyse continue sans social |
| **PostgreSQL** | Retry 3x, si échec → log error | Continue sans sauvegarder |
| **MT5 (données)** | Retry 3x, si échec → skip l'analyse | Pas d'analyse cette itération |
| **MT5 (exécution)** | Retry 3x, si échec → ne pas exécuter | Signal sauvé mais non exécuté |

> **Le bot ne crashe jamais définitivement.** Chaque appel externe est enveloppé dans un try/except avec retry.

---

## 🖥 Déploiement VPS

### Prérequis VPS

- VPS OVH (31 GB RAM, 8 cores) sous Ubuntu/Debian
- PostgreSQL installé et configuré
- Container Docker MT5 opérationnel sur le port 8001
- Python 3.10+ et Node.js 18+ installés

### Service systemd pour le bot Python

```ini
# /etc/systemd/system/tradebot.service

[Unit]
Description=Trade Bot SMC/ICT
After=network.target postgresql.service

[Service]
Type=simple
User=adam
WorkingDirectory=/home/adam/projet
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable tradebot
sudo systemctl start tradebot

# Vérifier le status
sudo systemctl status tradebot

# Voir les logs systemd
sudo journalctl -u tradebot -f
```

### Service systemd pour le dashboard Next.js

```ini
# /etc/systemd/system/dashboard.service

[Unit]
Description=Trade Bot Dashboard Next.js
After=network.target postgresql.service

[Service]
Type=simple
User=adam
WorkingDirectory=/home/adam/projet/dashboard
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

```bash
# Build avant de démarrer
cd /home/adam/projet/dashboard
npm run build

# Activer et démarrer
sudo systemctl daemon-reload
sudo systemctl enable dashboard
sudo systemctl start dashboard
```

### Nginx reverse proxy (optionnel)

```nginx
# /etc/nginx/sites-available/dashboard

server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔒 Sécurité

- **`.env` et `.env.local`** ne sont jamais commités (dans `.gitignore`)
- **Aucune clé API hardcodée** dans le code source — tout passe par `os.getenv()` / `dotenv`
- **Container Docker MT5** accessible uniquement en localhost (pas exposé sur le réseau)
- **NanoClaw** tourne dans un container Docker isolé avec filesystem isolation
- **Logs** exclus du versionning (dossier `logs/`)

---

## 🗺 Roadmap

| Phase | Description | Statut |
|-------|-------------|--------|
| **Phase 1** | Bot Python — analyse SMC/ICT, exécution MT5, LLM routing | ✅ Terminé |
| **Phase 2** | Dashboard Next.js — monitoring temps réel, PnL, logs, override | ✅ Terminé |
| **Phase 3** | Intégration NanoClaw — agent IA autonome Docker sur OVH | 🔜 À venir |
| **Phase 4** | Alertes Telegram — notifications trade ouvert/fermé, drawdown | 💡 Optionnel |

---

## 📄 Licence

MIT — libre d'utilisation, modification et distribution.

---

> **⚠️ Avertissement** : ce bot est utilisé en compte démo (Vantage International, 100€, levier 1:500). Le trading comporte des risques de perte en capital. Ce projet est à but éducatif et expérimental.
