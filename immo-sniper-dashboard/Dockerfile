FROM node:20-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src/ src/
COPY public/ public/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend
COPY --from=frontend /app/dist /app/dist

# Expose port
ENV PORT=5051
EXPOSE 5051

CMD ["gunicorn", "--bind", "0.0.0.0:5051", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
