# Start from Python image instead of nginx:alpine
FROM python:3.11-alpine

# Install dependencies
RUN apk add --no-cache nginx bash socat

# Set working directory
WORKDIR /app

# Copy application code
COPY app.py redispython.py try2.py /app/
COPY templates /app/templates
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Set up Nginx cache folder
RUN mkdir -p /var/cache/nginx/video_cache && chmod -R 777 /var/cache/nginx/video_cache

# Expose Flask and Nginx ports
EXPOSE 5000 8081

# Start Flask and Nginx
CMD ["sh", "-c", " python /app/app.py & nginx -g 'daemon off;'"]
