# Trade Bot - Spécification Technique

## Stratégie : SMC/ICT (Smart Money Concepts / Institutional Cut Theory)

---

## 1. ASSETS TRADÉS

| Asset | Type | Timeframe |
|-------|------|-----------|
| XAUUSD | Or spot CFD | M5 |
| US100 (NAS100.cash) | Nasdaq 100 Cash CFD | M5 |

**Risque par trade** : 1% du capital

---

## 2. SESSION DE TRADING

| Session | Horaire Paris | Rôle |
|---------|---------------|------|
| Asia | 00h00 - 09h00 | Préparation du marché |
| London | 09h00 - 14h30 | Préparation du marché |
| **New York** | **14h30 - 21h00** | **Session active de trading** |

**Règle** :
- UNIQUEMENT trading pendant New York (14h30 - 21h00 Paris)
- En dehors de New York → `{"direction": "none", "reason": "hors session"}`

**Timezone** : Toutes les heures sont gérées en Europe/Paris via `pytz` ou `zoneinfo`. Le VPS OVH est en UTC par défaut, donc conversion explicite nécessaire.

---

## 3. NIVEAUX CLÉS

Les niveaux suivants sont **fixes pour la journée** (calculés une fois au début de la journée) :

| Niveau | Définition |
|--------|------------|
| Asia High | Plus haut de 00h00 - 09h00 Paris |
| Asia Low | Plus bas de 00h00 - 09h00 Paris |
| London High | Plus haut de 09h00 - 14h30 Paris |
| London Low | Plus bas de 09h00 - 14h30 Paris |
| Previous Day High | Plus haut de la veille |
| Previous Day Low | Plus bas de la veille |

**Comportement** : Le marché dépasse souvent ces niveaux pour prendre les stops avant de réagir.

---

## 4. CONFLUENCES VALIDES

Le bot trade **UNIQUEMENT** sur des confluences :

| Symbole | Nom | Description |
|---------|-----|-------------|
| FVG | Fair Value Gap | Vide créé par mouvement rapide (3 bougies), zone de retour du prix |
| iFVG | Inverse FVG | FVG cassée qui devient zone de blocage ou continuation |
| OB | Order Block | Dernière bougie opposée avant un fort mouvement directionnel |
| BB | Breaker Block | Ancien OB cassé qui change de rôle |

---

## 5. 3 CONDITIONS OBLIGATOIRES POUR ENTRER

1. **Un niveau clé a été dépassé** → Liquidity Sweep confirmé
2. **Le prix revient dans une confluence** (FVG, OB, iFVG)
3. **Bougie de confirmation franche** dans le sens du trade

**Si une seule condition manque** → `trade_valid: false`

---

## 6. 2 SCÉNARIOS DE TRADING

### Scénario 1 - Reversal
- Le marché dépasse un niveau puis repart dans l'autre sens
- Les traders piégés ferment leurs positions
- On trade dans le sens inverse du sweep
- **Cible** : prochain high ou low visible opposé

### Scénario 2 - Continuation
- Le marché dépasse un niveau et continue dans le même sens
- La tendance est forte, pas de reversal
- **Cible** : prochain high ou low dans le sens du mouvement

---

## 7. STOP LOSS ET TAKE PROFIT

| Élément | Rôle |
|---------|-------|
| **SL** | Derrière le niveau dépassé (là où l'idée est invalidée) |
| **TP** | Prochain key level visible (Asia/London/PrevDay high ou low) |
| **IMPORTANT** | Ne jamais inventer des niveaux |

---

## 8. RÈGLE ANTI-OVERTRADE

- **Maximum 2 trades par jour** par asset
- Après 2 trades (TP ou SL) → stop jusqu'au lendemain
- Pas de setup valide = on ne trade pas
- **La patience est une position**

**Persistance** : Le compteur de 2 trades max est persisté en base de données (table `daily_trade_counts`). Au démarrage du bot, le compteur est rechargé depuis la DB pour éviter qu'un redémarrage le réinitialise à zéro.

---

## 9. CALCUL DU LOT SIZE

Le risque est de **1% du capital** par trade. La formule exacte :

```
lot_size = (capital * 0.01) / (distance_sl_en_pips * valeur_pip_par_lot)
```

Cette valeur est calculée dynamiquement à chaque trade :
- **Capital** : récupéré depuis MT5 via `account_info.balance`
- **Distance SL** : `|entry_price - sl_price|` converti en pips
- **Valeur pip par lot** : récupérer directement depuis MT5 via `symbol_info.trade_tick_value` ou `symbol_info.trade_contract_size`

### Implémentation MT5
```python
# Récupérer la valeur du pip depuis MT5
symbol_info = mt5.symbol_info(symbol)
tick_value = symbol_info.trade_tick_value  # Valeur pour 1 tick (pas de pip)
pip_value = tick_value  # Utiliser directement

lot_size = (capital * 0.01) / (distance_sl_pips * pip_value)
```

**Important** :
- XAUUSD : `trade_tick_value` ≈ 0.01 $ par pip pour 1 lot (chez Vantage)
- US100 : `trade_tick_value` ≈ 1 $ par pip pour 1 lot (chez Vantage)
- **Jamais de valeur hardcodée** - toujours récupérer depuis MT5

**Jamais de lot size fixe**.

---

## 10. DONNÉES REÇUES À CHAQUE ANALYSE

Le bot reçoit les données suivantes pour chaque analyse :

- **Identification** : Asset + heure exacte (timezone Paris)
- **Prix** : Prix actuel + OHLCV des 20 dernières bougies M5
- **Indicateurs** : RSI, MACD, EMA 20/50/200
- **Niveaux clés** : Asia High/Low, London High/Low, PrevDay High/Low
- **Confluences détectées** : FVG, OB, iFVG, sweep (calculés algorithmiquement)
- **News** : NewsAPI pour l'asset concerné
- **Sentiment social** : Reddit (r/Forex, r/Gold, r/investing, r/stocks)

---

## 11. FORMAT DE RÉPONSE OBLIGATOIRE

Le bot doit répondre **UNIQUEMENT** en JSON valide, rien d'autre :

```json
{
  "asset": "XAUUSD | US100",
  "direction": "long | short | none",
  "scenario": "reversal | continuation | unclear | none",
  "confidence": 0-100,
  "entry_price": float ou null,
  "sl_price": float ou null,
  "tp_price": float ou null,
  "rr_ratio": float ou null,
  "confluences_used": ["FVG", "OB", "sweep", ...],
  "sweep_level": "asia_high | asia_low | london_high | london_low | prev_high | prev_low | none",
  "news_sentiment": "bullish | bearish | neutral",
  "social_sentiment": "bullish | bearish | neutral",
  "trade_valid": true | false,
  "reason": "explication courte en français"
}
```

**Règles importantes** :
- Si `trade_valid: false` → `entry_price`, `sl_price`, `tp_price`, `rr_ratio` doivent être `null`
- Ne **JAMAIS** halluciner des niveaux ou des confluences non présents dans les données reçues

---

## 12. STACK TECHNIQUE

### Infrastructure

| Composant | Détail |
|-----------|--------|
| **VPS** | OVH 31GB RAM, 8 cores |
| **OS** | Linux (Ubuntu/Debian) |
| **Orchestration** | NanoClaw (agent IA autonome, Docker) |
| **MT5** | Docker container sur le VPS, port 8001 localhost |

### Langage & Runtime

| Composant | Détail |
|-----------|--------|
| **Langage** | Python |
| **IA principale** | MiniMax M2.5 API (tool use natif, agentic, compatible OpenAI SDK) |
| **IA fallback** | Groq API + Llama 3.3 70B (si MiniMax timeout ou indisponible) |

**Routing LLM** :
- MiniMax M2.5 est le cerveau principal — meilleur sur les tâches agentic/tool use
- Groq Llama 3.3 prend le relais automatiquement si MiniMax ne répond pas sous 10s
- Si fallback actif → `trade_valid: false` sauf signal très fort (confidence > 85)

### Données Marché

| Composant | Détail |
|-----------|--------|
| **Source** | MetaTrader 5 via mt5linux (RPyC) |
| **Connexion** | localhost:8001 (Docker container) |
| **Broker** | Vantage International (compte demo) - **Déjà connecté** |
| **Effet de levier** | 1:500 |
| **Capital demo** | 100€ |
| **Données** | OHLCV temps réel M5 |

### Base de données

| Table | Rôle |
|-------|------|
| `signals` | Chaque décision IA (entrée, sortie, raison) |
| `trades` | Résultat réel du trade (TP/SL/fermeture manuelle) |
| `performance_stats` | Agrégats par pattern (pour auto-calibration) |
| `daily_trade_counts` | Compteur journalier de trades (anti-overtrade) |
| `bot_state` | Persistance état entre redémarrages |

**Auto-calibration** : Le bot injecte un résumé des performances passées similaires dans chaque prompt pour que l'IA s'auto-calibre avec le temps.

### Données Sentiment

| Source | Détail |
|--------|--------|
| **News** | NewsAPI |
| **Reddit** | r/Forex, r/Gold (pour XAUUSD), r/investing, r/stocks (pour US100) |
| **Twitter** | twscrape (optionnel, sans credentials pour l'instant) |

### Interface & Monitoring

| Phase | Interface |
|-------|-----------|
| **Phase 1** | CLI |
| **Phase 2** | Dashboard Next.js (monitoring temps réel, PnL, logs agent, override manuel) |

**Telegram** : Optionnel — uniquement pour alertes critiques (trade ouvert/fermé, drawdown important) si le dashboard n'est pas sous les yeux. Pas de contrôle principal via Telegram.

---

## 13. ARCHITECTURE GLOBALE

```
┌──────────────────────────────────────────────────┐
│            Dashboard Next.js                     │
│  - Live trades / PnL                             │
│  - Logs agent en temps réel                      │
│  - Status des sources de data                    │
│  - Override manuel                               │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│              NanoClaw Agent (Docker OVH)         │
│  ┌─────────────────────────────────────────────┐ │
│  │  MiniMax M2.5 API (principal)               │ │
│  │  → Tool use natif, décisions agentic        │ │
│  └─────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────┐ │
│  │  Groq Llama 3.3 70B (fallback auto)         │ │
│  │  → Si MiniMax timeout ou indisponible       │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────┬───────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  Sources de données │
        │  ├── MT5 (prix live)│
        │  ├── NewsAPI        │
        │  ├── Reddit         │
        │  └── twscrape       │
        └──────────┬──────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│           MT5 Docker OVH                         │
│  ports 3001 / 8001                               │
│  ├── XAUUSD  (M5, session NY uniquement)         │
│  └── US100   (M5, session NY uniquement)         │
└──────────────────────────────────────────────────┘
```

---

## 14. FLUX DE TRAITEMENT

### Boucle principale (sur nouvelle bougie M5 uniquement)

**Important** : Le bot n'analyse PAS à intervalle fixe. Il vérifie si une nouvelle bougie M5 est fermée et n'appelle le LLM que dans ce cas.

```
[Timer: toutes les 10 secondes]
       │
       ▼
┌──────────────────┐
│1. Fetch dernières│
│   bougies MT5    │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│2. Comparer       │
│   timestamp avec │
│   dernière       │
│   analysée       │
└────────┬─────────┘
       │
       ▼
   [Nouvelle bougie ?]
       │
       ├─ NO ──→ Ne rien faire, attendre prochaine itération
       │
       └─ YES ──→ Suite du traitement
                   │
                   ▼
┌──────────────────┐
│3. Calcul niveaux │
│   Asia/London/   │
│   PrevDay        │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│4. Détect         │
│   confluences    │
│   FVG/OB/iFVG    │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│5. Fetch sentiment│
│   NewsAPI/Reddit │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│6. Query DB       │
│   Perf. patterns │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│7. Build prompt   │
│   + contexte     │
│   performances   │
└────────┬─────────┘
       │
       ▼
┌──────────────────────────────┐
│8. Call MiniMax M2.5 API      │
│   [si timeout → Groq fallback│
│    Llama 3.3 70B]            │
└────────┬─────────────────────┘
       │
       ▼
┌──────────────────┐
│9. Parse réponse  │
│   JSON strict    │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│10. Save signal   │
│    PostgreSQL    │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│11. Vérif         │
│    duplication   │
│    15 min window │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│12. Exécution     │
│    MT5 si valid  │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│13. Update        │
│    last_analyzed │
│    timestamp     │
└──────────────────┘
```

### Boucle de monitoring des trades (toutes les 30 secondes)
```
[Timer 30s]
       │
       ▼
┌──────────────────┐
│1. Fetch positions│
│   MT5            │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│2. Détect TP/SL   │
│   touched        │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│3. Update trades  │
│   table          │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│4. Update perf    │
│   stats          │
└────────┬─────────┘
       │
       ▼
┌──────────────────┐
│5. Incrémente     │
│   daily counter  │
└──────────────────┘
```

---

## 15. ORDRE DE DÉVELOPPEMENT

1. **Fallback agent Python custom** (base solide et testable indépendamment)
2. **MT5 Docker** branché dessus, tester les trades en demo
3. **NanoClaw** par dessus comme couche intelligente avec MiniMax M2.5
4. **Dashboard Next.js** pour monitorer tout ça en temps réel

---

## 16. GESTION DES ERREURS ET RÉSILIENCE

### Règle générale
Le bot ne doit **jamais crasher définitivement**. Chaque appel externe doit être dans un try/except avec retry automatique.

### Retry automatique
- **Max tentatives** : 3
- **Backoff** : exponentiel (30s → 60s → 120s)
- **Logging** : chaque tentative est loggée

### Dégradation gracieuse

| Service indisponible | Comportement |
|---------------------|--------------|
| **MiniMax API** | Switch automatique sur Groq fallback |
| **Groq API (fallback)** | `trade_valid: false`, reason: "llm_unavailable", continuer |
| **NewsAPI** | `news_sentiment: neutral`, continuer |
| **Reddit** | `social_sentiment: neutral`, continuer |
| **PostgreSQL** | Retry 3x, si échec → log error, continuer sans save |
| **MT5 (données)** | Retry 3x, si échec → skip analyse |
| **MT5 (exécution)** | Retry 3x, si échec → ne pas exécuter |

### Connexion MT5
Si la connexion RPyC échoue :
1. Logger l'erreur
2. Attendre 30 secondes
3. Réessayer (max 3 tentatives)
4. Si toujours échec → logger erreur critique, continuer la boucle

---

## 17. LOGS

### Configuration
- **Niveau INFO** : Chaque nouvelle bougie analysée, signal généré, trade exécuté
- **Niveau WARNING** : Setup détecté sans entrée valide
- **Niveau ERROR** : Échecs d'API, erreurs de connexion

### Fichiers
- **Emplacement** : `logs/bot.log`
- **Rotation** : Journalière (nouveau fichier chaque jour)
- **Rétention** : 30 jours

### Format
```
2026-02-23 14:30:00 [INFO] New M5 candle detected for XAUUSD
2026-02-23 14:30:00 [INFO] Analyzing XAUUSD at 2045.50
2026-02-23 14:30:01 [INFO] LLM: MiniMax M2.5 (principal)
2026-02-23 14:30:01 [INFO] Signal: short | Valid: True | Confidence: 75%
2026-02-23 14:30:02 [INFO] Trade executed: XAUUSD @ 2045.50, SL: 2046.00, TP: 2044.50
2026-02-23 14:35:00 [INFO] New M5 candle detected for US100 (no analysis - outside NY session)
2026-02-23 14:40:00 [WARNING] Setup detected but conditions not met for US100
2026-02-23 14:45:00 [WARNING] MiniMax timeout, switching to Groq fallback
2026-02-23 14:45:01 [INFO] LLM: Groq Llama 3.3 70B (fallback)
```

---

## 18. SÉCURITÉ

### .gitignore
Le fichier `.env` ne doit **jamais** être commité :
```
.env
.env.*
*.log
logs/
__pycache__/
*.pyc
.pytest_cache/
```

### Variables d'environnement
- Les API keys ne doivent **jamais** apparaître dans le code source
- Utiliser uniquement `os.getenv()` ou `python-dotenv`
- Aucune clé hardcodée

### NanoClaw & isolation
NanoClaw tourne dans un container Docker sur OVH avec filesystem isolation. Les agents n'ont accès qu'à ce qui est explicitement monté — le reste du système est hors de portée.

---

## 19. DÉDUPLICATION DES SIGNAUX

Avant d'exécuter un trade, vérifier dans la table `signals` :
- **Critères** : même asset, même direction, même sweep_level
- **Fenêtre** : 15 dernières minutes
- **Action** : si match trouvé → ne pas exécuter, logger "duplicate signal skipped"

---

## 20. API KEYS & CREDENTIALS

### MiniMax API (principal)
```
Base URL: https://api.minimax.io/v1
API Key: (dans .env)
Compatible OpenAI SDK: oui
```

### Groq API (fallback)
```
API Key: (dans .env)
Model: llama-3.3-70b-versatile
```

### NewsAPI
```
API Key: (dans .env)
```

### Reddit API
```
Client ID: (dans .env - optionnel)
Client Secret: (dans .env - optionnel)
User Agent: trade_bot/1.0

Note: Optionnel. Si les credentials sont vides, le module Reddit tourne sans erreur.
Pour créer: reddit.com/prefs/apps → app script → http://localhost:8080
```

### PostgreSQL
```
Host: localhost
Port: 5432
Database: trade
Username: adam
Password: (dans .env)
```

### MetaTrader 5
```
Connexion: localhost:8001 (Docker RPyC)
Server: VantageInternational-Demo
Note: MT5 tourne en container Docker sur le VPS
```

---

## 21. SCHÉMA BASE DE DONNÉES (PostgreSQL)

### Table : signals

```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    direction VARCHAR(10),
    scenario VARCHAR(20),
    confidence INTEGER,
    entry_price DECIMAL(12,5),
    sl_price DECIMAL(12,5),
    tp_price DECIMAL(12,5),
    rr_ratio DECIMAL(5,2),
    confluences_used TEXT[],
    sweep_level VARCHAR(20),
    news_sentiment VARCHAR(10),
    social_sentiment VARCHAR(10),
    trade_valid BOOLEAN,
    reason TEXT,
    executed BOOLEAN DEFAULT FALSE,
    llm_used VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_signals_asset_timestamp ON signals(asset, timestamp);
CREATE INDEX idx_signals_trade_valid ON signals(trade_valid);
CREATE INDEX idx_signals_recent_dedup ON signals(asset, direction, sweep_level, timestamp)
    WHERE timestamp > NOW() - INTERVAL '15 minutes';
```

### Table : trades

```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    asset VARCHAR(10) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(12,5) NOT NULL,
    exit_price DECIMAL(12,5),
    sl_price DECIMAL(12,5),
    tp_price DECIMAL(12,5),
    lot_size DECIMAL(10,5),
    pnl DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'open',
    closed_reason VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_signal_id ON trades(signal_id);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_asset_entry ON trades(asset, entry_time);
```

### Table : performance_stats

```sql
CREATE TABLE performance_stats (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(50) NOT NULL,
    asset VARCHAR(10),
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_rr DECIMAL(5,2),
    total_pnl DECIMAL(15,2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pattern_type, asset)
);

CREATE INDEX idx_perf_pattern_asset ON performance_stats(pattern_type, asset);
```

### Table : daily_trade_counts

```sql
CREATE TABLE daily_trade_counts (
    id SERIAL PRIMARY KEY,
    asset VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    closed_trades INTEGER DEFAULT 0,
    UNIQUE(asset, trade_date)
);

CREATE INDEX idx_daily_counts ON daily_trade_counts(asset, trade_date);
```

### Table : bot_state

```sql
CREATE TABLE bot_state (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO bot_state (key, value) VALUES ('last_analyzed_XAUUSD', '')
ON CONFLICT (key) DO NOTHING;
INSERT INTO bot_state (key, value) VALUES ('last_analyzed_US100', '')
ON CONFLICT (key) DO NOTHING;
```

---

## 22. PROMPT SYSTÈME IA

```
Tu es un algorithme de trading expert basé sur la stratégie SMC/ICT.

## ASSETS TRADÉS
- XAUUSD (Or spot CFD)
- US100 (Nasdaq 100 Cash CFD)
Timeframe : M5
Risque par trade : 1% du capital

## SESSION DE TRADING
Tu trades UNIQUEMENT pendant la session New York (14h30 - 21h00 heure de Paris).
Asia et London préparent le marché. New York fait le vrai mouvement.
En dehors de New York → {"direction": "none", "reason": "hors session"}

## NIVEAUX CLÉS (fournis à chaque analyse)
- Asia High / Asia Low (00h00 - 09h00 Paris)
- London High / London Low (09h00 - 14h30 Paris)
- Previous Day High / Previous Day Low
Ces niveaux sont fixes pour la journée.
Le marché les dépasse souvent pour prendre les stops avant de réagir.

## CONFLUENCES REQUISES
Tu ne trades JAMAIS sans confluence. Confluences valides :
- FVG (Fair Value Gap) : vide créé par mouvement rapide, 3 bougies, zone de retour du prix
- iFVG (Inverse FVG) : FVG cassée qui devient zone de blocage ou continuation
- OB (Order Block) : dernière bougie opposée avant un fort mouvement directionnel
- BB (Breaker Block) : ancien OB cassé qui change de rôle

## 3 CONDITIONS OBLIGATOIRES POUR ENTRER

1. Un niveau clé a été dépassé → Liquidity Sweep confirmé
2. Le prix revient dans une confluence (FVG, OB, iFVG)
3. Bougie de confirmation franche dans le sens du trade

Si une seule condition manque → trade_valid: false

## 2 SCÉNARIOS POSSIBLES

Scénario 1 - Reversal :
Le marché dépasse un niveau puis repart dans l'autre sens.
Les traders piégés ferment → on trade dans le sens inverse du sweep.
Cible : prochain high ou low visible opposé.

Scénario 2 - Continuation :
Le marché dépasse un niveau et continue dans le même sens.
La tendance est forte, pas de reversal.
Cible : prochain high ou low dans le sens du mouvement.

## STOP LOSS ET TAKE PROFIT
- SL : derrière le niveau dépassé (là où l'idée est invalidée)
- TP : prochain key level visible sur le graphique (Asia/London/PrevDay high ou low)
- Ne jamais inventer des niveaux

## RÈGLE ANTI-OVERTRADE
- Maximum 2 trades par jour par asset
- Après 2 trades (TP ou SL) → stop jusqu'au lendemain
- Pas de setup valide = on ne trade pas
- La patience est une position

## DONNÉES REÇUES À CHAQUE ANALYSE
- Asset + heure exacte (timezone Paris)
- Prix actuel + OHLCV des 20 dernières bougies M5
- RSI, MACD, EMA 20/50/200
- Asia High/Low, London High/Low, PrevDay High/Low
- Confluences détectées : FVG, OB, iFVG, sweep (calculés algorithmiquement)
- News récentes sur l'asset (NewsAPI)
- Sentiment Reddit (r/Forex, r/Gold pour XAUUSD / r/investing, r/stocks pour US100)
- Stats de performances passées pour patterns similaires (auto-calibration)

## FORMAT DE RÉPONSE OBLIGATOIRE
Réponds UNIQUEMENT en JSON valide, rien d'autre :

{
  "asset": "XAUUSD | US100",
  "direction": "long | short | none",
  "scenario": "reversal | continuation | unclear | none",
  "confidence": 0-100,
  "entry_price": float ou null,
  "sl_price": float ou null,
  "tp_price": float ou null,
  "rr_ratio": float ou null,
  "confluences_used": ["FVG", "OB", "sweep", ...],
  "sweep_level": "asia_high | asia_low | london_high | london_low | prev_high | prev_low | none",
  "news_sentiment": "bullish | bearish | neutral",
  "social_sentiment": "bullish | bearish | neutral",
  "trade_valid": true | false,
  "reason": "explication courte en français"
}

Si trade_valid est false → entry_price, sl_price, tp_price, rr_ratio sont null.
Ne jamais halluciner des niveaux ou des confluences non présents dans les données reçues.
```

---

## 23. FICHIER CONFIG (.env)

```env
# MiniMax API (principal)
MINIMAX_API_KEY=ton_api_key
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-M2.5
LLM_TIMEOUT=10

# Groq (fallback)
GROQ_API_KEY=ton_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# NewsAPI
NEWSAPI_KEY=ton_api_key

# Reddit (optionnel - laisser vide si non utilisé)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=trade_bot/1.0

# PostgreSQL (VPS)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trade
DB_USER=adam
DB_PASSWORD=

# MetaTrader 5 (Docker RPyC)
MT5_HOST=localhost
MT5_PORT=8001
```

---

## 24. .GITIGNORE

```
# Environment
.env
.env.*
.env.local

# Logs
logs/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Debug
*.bak
*.tmp
```

---

*Document de référence pour le bot de trading SMC/ICT*
*Stack : Python + MT5 Docker + NanoClaw + MiniMax M2.5 (fallback Groq Llama 3.3) + PostgreSQL + Dashboard Next.js*
*VPS OVH — Broker Vantage International (demo)*
