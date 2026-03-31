FROM nginx:alpine

# Copy site files
COPY . /usr/share/nginx/html

# Remove Dockerfile from served files
RUN rm -f /usr/share/nginx/html/Dockerfile

# Render uses port 10000 by default for free tier
# Configure nginx to listen on PORT env var (default 10000)
RUN echo 'server { listen 10000; server_name _; root /usr/share/nginx/html; index index.html; location / { try_files $uri $uri/ /index.html; } }' > /etc/nginx/conf.d/default.conf

EXPOSE 10000

CMD ["nginx", "-g", "daemon off;"]
