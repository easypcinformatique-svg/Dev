FROM python:3.12-slim

WORKDIR /app

# Copier et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Lancer en mode live avec dashboard (le port est lu depuis $PORT)
CMD ["python", "-m", "sale_alert.src.main", "--mode", "live", "--dashboard"]
