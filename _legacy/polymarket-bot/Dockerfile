FROM python:3.11-slim

WORKDIR /app

# Installer les dependances systeme
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dependances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copier le code source
COPY . .

# Lancer le bot avec dashboard (le port est lu depuis $PORT)
CMD ["python", "hedge_fund_bot.py", "--dashboard"]
