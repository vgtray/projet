FROM gmag11/metatrader5_vnc

# Fix RPyC Linux
RUN pip install --break-system-packages rpyc==5.2.3 plumbum==1.7.0 pyparsing==3.1.0 --force-reinstall

# Fix le script start.sh pour ne pas passer -w wine python.exe
RUN sed -i 's/python3 -m mt5linux --host 0.0.0.0 -p $mt5server_port -w $wine_executable python.exe/python3 -m mt5linux --host 0.0.0.0 -p $mt5server_port/' /Metatrader/start.sh

# Installe Python3 venv et pip proprement
RUN apt-get update && apt-get install -y python3-pip python3-venv python3-full --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Copie le projet
WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv /app/venv && /app/venv/bin/pip install --upgrade pip && /app/venv/bin/pip install -r requirements.txt

COPY . .

# Crée le dossier logs
RUN mkdir -p /app/logs

# Script de démarrage custom
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
