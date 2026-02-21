#!/bin/bash
set -e

echo "=== Démarrage MT5 + Wine ==="
/init &

echo "=== Attente du serveur RPyC MT5 (port 8001) ==="
MAX_WAIT=120
WAITED=0
while ! ss -tlnp | grep -q ':8001'; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "ERREUR: MT5 RPyC server n'a pas démarré après ${MAX_WAIT}s"
        exit 1
    fi
    echo "Attente MT5... (${WAITED}s)"
    sleep 5
    WAITED=$((WAITED + 5))
done

echo "=== MT5 RPyC prêt ! Attente stabilisation (10s) ==="
sleep 10

echo "=== Lancement du bot de trading ==="
exec /app/venv/bin/python /app/main.py
