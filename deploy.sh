#!/bin/bash

# Optimized Chatbot Deployment Script
# This script will set up your chatbot for production deployment

set -e

echo "🚀 Starting Optimized Chatbot Deployment Setup..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed ✅"
}

# Create project structure
create_structure() {
    print_status "Creating optimized project structure..."
    
    # Create directories
    mkdir -p backend/{models,routes,utils,tests}
    mkdir -p frontend/{src/{components,utils,styles},public}
    mkdir -p nginx
    mkdir -p mysql/conf.d
    mkdir -p data/{mysql,redis,chroma}
    
    print_status "Project structure created ✅"
}

# Create backend Dockerfile
create_backend_dockerfile() {
    print_status "Creating optimized backend Dockerfile..."
    
    cat > backend/Dockerfile << 'EOF'
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Use uvicorn with multiple workers for production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

    print_status "Backend Dockerfile created ✅"
}

# Create frontend Dockerfile
create_frontend_dockerfile() {
    print_status "Creating optimized frontend Dockerfile..."
    
    cat > frontend/Dockerfile << 'EOF'
# Multi-stage build for smaller image size
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Add non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

# Set permissions
RUN chown -R nextjs:nodejs /usr/share/nginx/html && \
    chown -R nextjs:nodejs /var/cache/nginx

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80 || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
EOF

    print_status "Frontend Dockerfile created ✅"
}

# Create nginx configuration
create_nginx_config() {
    print_status "Creating optimized Nginx configuration..."
    
    cat > nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Performance optimizations
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    server {
        listen 80;
        server_name localhost;
        root /usr/share/nginx/html;
        index index.html;
        
        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            access_log off;
        }
        
        # Handle React Router
        location / {
            try_files $uri $uri/ /index.html;
        }
        
        # Proxy API calls to backend with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeout settings
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
            
            # Buffer settings
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }
    }
}
EOF

    print_status "Nginx configuration created ✅"
}

# Create MySQL configuration
create_mysql_config() {
    print_status "Creating MySQL configuration..."
    
    cat > mysql/conf.d/custom.cnf << 'EOF'
[mysqld]
# Performance optimizations
innodb_buffer_pool_size = 256M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Connection settings
max_connections = 200
wait_timeout = 300
interactive_timeout = 300

# Query cache
query_cache_type = 1
query_cache_size = 32M

# Character set
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# Logging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
EOF

    print_status "MySQL configuration created ✅"
}

# Create environment file
create_env_file() {
    print_status "Creating environment configuration..."
    
    if [ ! -f .env ]; then
        cp .env.example .env
        print_warning "Please update the .env file with your actual API keys and secrets"
    else
        print_status "Environment file already exists"
    fi
}

# Create deployment scripts
create_deployment_scripts() {
    print_status "Creating deployment scripts..."
    
    # Start script
    cat > start.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting Optimized Chatbot..."
docker-compose up --build -d
echo "✅ Chatbot started successfully!"
echo "Frontend: http://localhost"
echo "Backend API: http://localhost:8000"
echo "Health Check: http://localhost:8000/api/health"
EOF

    # Stop script
    cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 Stopping Optimized Chatbot..."
docker-compose down
echo "✅ Chatbot stopped successfully!"
EOF

    # Update script
    cat > update.sh << 'EOF'
#!/bin/bash
echo "🔄 Updating Optimized Chatbot..."
docker-compose down
docker-compose pull
docker-compose up --build -d
echo "✅ Chatbot updated successfully!"
EOF

    # Logs script
    cat > logs.sh << 'EOF'
#!/bin/bash
echo "📋 Showing Chatbot Logs..."
docker-compose logs -f --tail=100
EOF

    # Make scripts executable
    chmod +x start.sh stop.sh update.sh logs.sh
    
    print_status "Deployment scripts created ✅"
}

# Create monitoring script
create_monitoring() {
    print_status "Creating monitoring script..."
    
    cat > monitor.sh << 'EOF'
#!/bin/bash

echo "📊 Chatbot Performance Monitor"
echo "==============================="

# Check container status
echo "🐳 Container Status:"
docker-compose ps

echo ""
echo "💾 Memory Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

echo ""
echo "🌐 Health Checks:"
echo -n "Backend Health: "
curl -s http://localhost:8000/api/health | jq -r '.status // "FAILED"' 2>/dev/null || echo "FAILED"

echo -n "Frontend Health: "
curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null | grep -q "200" && echo "HEALTHY" || echo "FAILED"

echo ""
echo "📊 Backend Stats:"
curl -s http://localhost:8000/api/stats 2>/dev/null | jq . || echo "Stats unavailable"
EOF

    chmod +x monitor.sh
    
    print_status "Monitoring script created ✅"
}

# Main installation function
main() {
    print_status "🎯 Optimized Chatbot Deployment Setup"
    print_status "======================================"
    
    # Check prerequisites
    check_docker
    
    # Create project structure
    create_structure
    
    # Create Docker configurations
    create_backend_dockerfile
    create_frontend_dockerfile
    create_nginx_config
    create_mysql_config
    
    # Create environment configuration
    create_env_file
    
    # Create deployment scripts
    create_deployment_scripts
    create_monitoring
    
    print_status "🎉 Setup completed successfully!"
    print_status ""
    print_status "Next steps:"
    print_status "1. Copy your existing code to the backend/ and frontend/ directories"
    print_status "2. Update the .env file with your API keys"
    print_status "3. Run: ./start.sh to deploy your optimized chatbot"
    print_status "4. Monitor with: ./monitor.sh"
    print_status ""
    print_status "Your optimized chatbot will be available at:"
    print_status "- Frontend: http://localhost"
    print_status "- Backend API: http://localhost:8000"
    print_status "- Health Check: http://localhost:8000/api/health"
}

# Run the main function
main "$@"