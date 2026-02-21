FROM gmag11/metatrader5_vnc

# Fix RPyC Linux
RUN pip install --break-system-packages rpyc==5.2.3 plumbum==1.7.0 pyparsing==3.1.0 --force-reinstall

# Fix NumPy conflict dans Wine Python (MetaTrader5 nécessite numpy<2)
ENV WINEPREFIX=/config/.wine
RUN wine python -m pip install "numpy<2" --quiet 2>/dev/null || true

# Remplace le serveur RPyC Linux par Wine Python (seul capable d'importer MetaTrader5)
RUN sed -i 's|python3 -m mt5linux --host 0.0.0.0 -p \$mt5server_port|wine python -m mt5linux --host 0.0.0.0 -p \$mt5server_port|g' /Metatrader/start.sh

# Supprime le repo WineHQ (clé GPG expirée) - Wine déjà installé dans l'image de base
RUN rm -f /etc/apt/sources.list.d/winehq* /etc/apt/sources.list.d/wine* 2>/dev/null || true && \
    apt-get update && \
    apt-get install -y python3-pip python3-venv python3-full --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copie le projet
WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv /app/venv && /app/venv/bin/pip install --upgrade pip && /app/venv/bin/pip install -r requirements.txt

COPY . .
RUN mkdir -p /app/logs

# Crée le service s6 pour le bot (démarre APRÈS /init qui gère Xvfb + Wine + MT5 + RPyC)
RUN mkdir -p /etc/services.d/trade-bot
COPY docker-entrypoint.sh /etc/services.d/trade-bot/run
RUN chmod +x /etc/services.d/trade-bot/run
