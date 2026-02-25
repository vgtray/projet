# AGENTS.md - Development Guide for AI Agents

This document provides guidelines for agents working on this codebase.

## Project Overview

This is a **SMC/ICT trading bot** with two main components:
- **Python bot** (`src/`, `main.py`): Trading logic, LLM integration, MT5 execution
- **Next.js dashboard** (`dashboard/`): Real-time monitoring interface

## Build, Lint & Test Commands

### Python Bot

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py

# No tests configured - this project uses manual testing
# No linting configured for Python
```

### Dashboard (Next.js)

```bash
# Navigate to dashboard
cd dashboard

# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Start production server
npm run start

# Lint (ESLint)
npm run lint

# Run a single test file (if tests exist)
npx vitest run path/to/test.test.ts

# Run tests in watch mode
npx vitest
```

### Database

```bash
# Initialize PostgreSQL schema (idempotent)
psql -d trade -f sql/init.sql
```

## Code Style Guidelines

### Python Backend

**Imports**
- Use absolute imports from `src.` package
- Order: stdlib → third-party → local
- Example:
  ```python
  import logging
  import signal
  from datetime import datetime
  
  import pytz
  
  from src.config import Config
  from src.database import Database
  ```

**Naming Conventions**
- Classes: `PascalCase` (e.g., `TradingBot`, `LLMClient`)
- Functions/methods: `snake_case` (e.g., `calculate_all`, `get_candles`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_TRADES_PER_DAY`)
- Private methods: `_leading_underscore` (e.g., `_analyze_asset`)
- Types: Use typing module (e.g., `Optional[str]`, `dict[str, Any]`)

**Formatting**
- 4 spaces for indentation
- Max line length: 100 characters (soft guideline)
- Use f-strings for formatting
- Add type hints to function signatures

**Error Handling**
- Wrap external calls in try/except with specific exceptions
- Always log errors with `logger.error(..., exc_info=True)`
- Use graceful degradation patterns (don't crash on API failures)
- Return fallback values instead of raising when appropriate

**Database**
- Use parameterized queries to prevent SQL injection
- Use context managers for cursor operations:
  ```python
  with self.db.conn.cursor() as cur:
      cur.execute("SELECT * FROM table WHERE id = %s", (id,))
  ```

**Logging**
- Use the module logger: `logger = logging.getLogger(__name__)`
- Use appropriate levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include context in log messages (e.g., asset, trade_id)

### TypeScript/Next.js Dashboard

**Imports**
- Use path aliases configured in tsconfig (`@/` for `src/`)
- Order: React/Next → external libs → local components/utils
- Example:
  ```typescript
  import { useState, useEffect } from 'react';
  import { format } from 'date-fns';
  
  import { cn } from '@/lib/utils';
  import { StatsBar } from '@/components/StatsBar';
  ```

**Naming Conventions**
- Components: `PascalCase` (e.g., `BotStatus.tsx`, `TradeRow.tsx`)
- Hooks: `camelCase` starting with `use` (e.g., `useTrades`)
- Utility functions: `camelCase` (e.g., `formatPrice`, `cn`)
- Types/Interfaces: `PascalCase` (e.g., `Trade`, `Signal`)
- Files: `kebab-case` for non-component files (e.g., `db.ts`, `utils.ts`)

**Formatting**
- Use ESLint and Prettier (project uses Tailwind CSS v4)
- 2 spaces for indentation
- Use TypeScript strict mode
- Prefer interface over type for object shapes

**Types**
- Always define types for API responses and props
- Use explicit return types for utility functions
- Avoid `any` - use `unknown` if type is truly unknown

**Components**
- Use functional components with hooks
- Keep components small and focused
- Extract reusable logic into custom hooks
- Use proper TypeScript typing for props

**Tailwind CSS**
- Use utility classes from Tailwind v4
- Use `cn()` utility for conditional class merging
- Follow existing color scheme (zinc, emerald, red for PnL)

**API Routes**
- Follow Next.js App Router conventions (`route.ts`)
- Use proper HTTP method handling (GET, POST)
- Return JSON responses with appropriate status codes

### Database Schema

- Table names: `snake_case` (e.g., `signals`, `trades`, `bot_state`)
- Columns: `snake_case` (e.g., `entry_price`, `created_at`)
- Use PostgreSQL-specific features: `TIMESTAMPTZ`, `TEXT[]`, `DECIMAL`

### Git Conventions

- Commit messages: Clear, concise, in English or French
- Branch naming: `feature/description` or `fix/description`
- Never commit secrets (use `.env` files excluded from git)

### Testing

This project currently has **no automated tests**. When adding tests:
- Python: Use `pytest` with fixtures
- TypeScript: Use `vitest` (already configured in Next.js projects)
- Follow existing code conventions in test files
- Test both success and failure paths

### Documentation

- Add docstrings to public classes and functions (Google style for Python)
- Comment complex business logic
- Update README.md for user-facing changes
- Keep SPEC.md in sync with implementation

### Security

- Never hardcode API keys or secrets
- Use environment variables via `os.getenv()` or `process.env`
- Validate all user inputs
- Use parameterized queries for database operations

### Authentication (Better Auth)

The dashboard uses Better Auth for authentication.

**Setup:**
```bash
# Run the better-auth schema migration
psql -d trade -f dashboard/sql/better-auth.sql

# Generate a secret key (min 32 chars)
openssl rand -base64 32
```

**Environment Variables (dashboard/.env.local):**
```bash
BETTER_AUTH_SECRET=your_generated_secret
BETTER_AUTH_URL=http://localhost:3000
```

**Protected Routes:**
- All pages except `/login` require authentication
- All API routes except `/api/auth/*` require authentication
- Middleware: `dashboard/src/middleware.ts`

**Files:**
- Server config: `dashboard/src/lib/auth.ts`
- Client config: `dashboard/src/lib/auth-client.ts`
- Auth provider: `dashboard/src/components/AuthProvider.tsx`
- Login page: `dashboard/src/app/login/page.tsx`
- API route: `dashboard/src/app/api/auth/[...all]/route.ts`

### File Structure Reference

```
projet/
├── main.py                    # Bot entry point
├── src/                       # Python source
│   ├── config.py              # Configuration
│   ├── bot.py                 # Main orchestration
│   ├── llm_client.py          # LLM integration
│   ├── mt5_client.py          # MetaTrader client
│   ├── database.py            # PostgreSQL operations
│   ├── key_levels.py          # Key level calculations
│   ├── confluences.py         # FVG/OB detection
│   ├── indicators.py          # RSI/MACD/EMA
│   ├── sentiment.py           # News/Reddit sentiment
│   └── logging_setup.py       # Logging configuration
├── sql/
│   └── init.sql               # Database schema
└── dashboard/                 # Next.js dashboard
    ├── src/app/               # App Router pages
    ├── src/components/        # React components
    └── src/lib/               # Utilities
```
