#!/bin/bash
# Service s6 : lancé automatiquement par /init après Wine + MT5 + RPyC

echo "=== [trade-bot] Attente du serveur RPyC MT5 (port 8001) ==="
MAX_WAIT=300
WAITED=0
while ! ss -tlnp | grep -q ':8001'; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "[trade-bot] ERREUR: RPyC non disponible après ${MAX_WAIT}s, on réessaie dans 60s"
        sleep 60
        WAITED=0
    fi
    echo "[trade-bot] Attente MT5 RPyC... (${WAITED}s/${MAX_WAIT}s)"
    sleep 10
    WAITED=$((WAITED + 10))
done

echo "=== [trade-bot] Port 8001 ouvert. Stabilisation 30s ==="
sleep 30

echo "=== [trade-bot] Lancement du bot ==="
exec /app/venv/bin/python /app/main.py
