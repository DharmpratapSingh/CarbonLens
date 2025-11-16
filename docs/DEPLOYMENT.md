# ClimateGPT Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-16

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Database Setup](#database-setup)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11.x | Runtime environment |
| uv | Latest | Package management |
| Docker | 20.10+ | Containerization (optional) |
| Docker Compose | 2.0+ | Multi-container orchestration (optional) |
| Git | 2.0+ | Version control |

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 10 GB
- OS: Linux, macOS, Windows (WSL2)

**Recommended:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 20+ GB SSD
- OS: Linux (Ubuntu 20.04+)

**Production:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 50+ GB SSD with high IOPS
- OS: Linux (Ubuntu 22.04 LTS)

---

## Local Development

### Option 1: Using Make (Recommended)

#### 1. Clone Repository

```bash
git clone https://github.com/DharmpratapSingh/Team-1B-Fusion.git
cd Team-1B-Fusion
```

#### 2. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

#### 3. Configure Environment

```bash
# Create .env file
cat > .env << 'EOF'
# Required
OPENAI_API_KEY=username:password

# Optional (defaults shown)
DB_PATH=data/warehouse/climategpt.duckdb
DB_POOL_SIZE=10
LLM_CONCURRENCY_LIMIT=10
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000
EOF
```

#### 4. Start Services

**Terminal 1 - Start MCP Server:**
```bash
make serve
# Starts MCP HTTP Bridge + stdio server on port 8010
```

**Terminal 2 - Start UI:**
```bash
make ui
# Starts Streamlit UI on port 8501
```

#### 5. Access Application

- **UI:** http://localhost:8501
- **API Docs:** http://localhost:8010/docs
- **Health Check:** http://localhost:8010/health

### Option 2: Manual Setup

#### Start MCP Server

```bash
# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Start server
python mcp_http_bridge.py
```

#### Start Streamlit UI

```bash
# In separate terminal
source .venv/bin/activate

# Start UI
streamlit run enhanced_climategpt_with_personas.py
```

---

## Docker Deployment

### Quick Start with Docker Compose

#### 1. Clone Repository

```bash
git clone https://github.com/DharmpratapSingh/Team-1B-Fusion.git
cd Team-1B-Fusion
```

#### 2. Create Environment File

```bash
cat > .env << 'EOF'
# Required
OPENAI_API_KEY=your_username:your_password

# Optional - Production Settings
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourdomain.com
DB_POOL_SIZE=20
LLM_CONCURRENCY_LIMIT=15
RATE_LIMIT_MAX_REQUESTS=200
RATE_LIMIT_WINDOW_SECONDS=60
CACHE_SIZE=2000
CACHE_TTL_SECONDS=600
EOF
```

#### 3. Build and Start

```bash
# Build images
docker compose build

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

#### 4. Verify Deployment

```bash
# Check service status
docker compose ps

# Test health endpoint
curl http://localhost:8010/health

# Access UI
open http://localhost:8501
```

#### 5. Manage Services

```bash
# Stop services
docker compose stop

# Restart services
docker compose restart

# View logs for specific service
docker compose logs -f server

# Scale UI instances
docker compose up -d --scale ui=3

# Remove all containers
docker compose down
```

### Custom Docker Configuration

#### Build Custom Image

Create `Dockerfile.custom`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Create volume mount point for database
VOLUME ["/app/data"]

# Expose ports
EXPOSE 8010 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8010/health || exit 1

# Default command
CMD ["python", "mcp_http_bridge.py"]
```

Build and run:

```bash
docker build -f Dockerfile.custom -t climategpt:custom .
docker run -p 8010:8010 -v $(pwd)/data:/app/data climategpt:custom
```

---

## Production Deployment

### Option 1: Docker Swarm

#### 1. Initialize Swarm

```bash
docker swarm init
```

#### 2. Create Stack File

`docker-stack.yml`:

```yaml
version: '3.9'

services:
  server:
    image: climategpt:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    ports:
      - "8010:8010"
    volumes:
      - climategpt-data:/app/data
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENVIRONMENT=production
      - DB_POOL_SIZE=20
      - LLM_CONCURRENCY_LIMIT=15
    networks:
      - climategpt-network

  ui:
    image: climategpt-ui:latest
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    ports:
      - "8501:8501"
    environment:
      - MCP_BRIDGE_URL=http://server:8010
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - climategpt-network
    depends_on:
      - server

volumes:
  climategpt-data:

networks:
  climategpt-network:
    driver: overlay
```

#### 3. Deploy Stack

```bash
docker stack deploy -c docker-stack.yml climategpt
```

#### 4. Manage Stack

```bash
# List services
docker service ls

# Scale service
docker service scale climategpt_server=5

# View logs
docker service logs -f climategpt_server

# Update service
docker service update --image climategpt:v2 climategpt_server

# Remove stack
docker stack rm climategpt
```

### Option 2: Kubernetes

#### 1. Create Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: climategpt
```

```bash
kubectl apply -f namespace.yaml
```

#### 2. Create ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: climategpt-config
  namespace: climategpt
data:
  ENVIRONMENT: "production"
  DB_POOL_SIZE: "20"
  LLM_CONCURRENCY_LIMIT: "15"
  CACHE_SIZE: "2000"
  RATE_LIMIT_MAX_REQUESTS: "200"
  ALLOWED_ORIGINS: "https://climategpt.example.com"
```

```bash
kubectl apply -f configmap.yaml
```

#### 3. Create Secrets

```bash
kubectl create secret generic climategpt-secrets \
  --from-literal=OPENAI_API_KEY='username:password' \
  -n climategpt
```

#### 4. Create PersistentVolumeClaim

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: climategpt-db-pvc
  namespace: climategpt
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd
```

```bash
kubectl apply -f pvc.yaml
```

#### 5. Deploy Server

```yaml
# server-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: climategpt-server
  namespace: climategpt
spec:
  replicas: 3
  selector:
    matchLabels:
      app: climategpt-server
  template:
    metadata:
      labels:
        app: climategpt-server
    spec:
      containers:
      - name: server
        image: climategpt:latest
        ports:
        - containerPort: 8010
        envFrom:
        - configMapRef:
            name: climategpt-config
        - secretRef:
            name: climategpt-secrets
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        volumeMounts:
        - name: db-storage
          mountPath: /app/data
        livenessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8010
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: db-storage
        persistentVolumeClaim:
          claimName: climategpt-db-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: climategpt-server
  namespace: climategpt
spec:
  selector:
    app: climategpt-server
  ports:
  - port: 8010
    targetPort: 8010
  type: ClusterIP
```

```bash
kubectl apply -f server-deployment.yaml
```

#### 6. Deploy UI

```yaml
# ui-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: climategpt-ui
  namespace: climategpt
spec:
  replicas: 2
  selector:
    matchLabels:
      app: climategpt-ui
  template:
    metadata:
      labels:
        app: climategpt-ui
    spec:
      containers:
      - name: ui
        image: climategpt-ui:latest
        ports:
        - containerPort: 8501
        env:
        - name: MCP_BRIDGE_URL
          value: "http://climategpt-server:8010"
        envFrom:
        - secretRef:
            name: climategpt-secrets
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: climategpt-ui
  namespace: climategpt
spec:
  selector:
    app: climategpt-ui
  ports:
  - port: 8501
    targetPort: 8501
  type: LoadBalancer
```

```bash
kubectl apply -f ui-deployment.yaml
```

#### 7. Create Ingress (Optional)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: climategpt-ingress
  namespace: climategpt
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - climategpt.example.com
    secretName: climategpt-tls
  rules:
  - host: climategpt.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: climategpt-server
            port:
              number: 8010
      - path: /
        pathType: Prefix
        backend:
          service:
            name: climategpt-ui
            port:
              number: 8501
```

```bash
kubectl apply -f ingress.yaml
```

#### 8. Verify Deployment

```bash
# Check pods
kubectl get pods -n climategpt

# Check services
kubectl get svc -n climategpt

# View logs
kubectl logs -f deployment/climategpt-server -n climategpt

# Get external IP
kubectl get svc climategpt-ui -n climategpt
```

---

## Environment Configuration

### Complete Environment Variable Reference

#### Required Variables

```bash
# API credentials (REQUIRED)
OPENAI_API_KEY=username:password
```

#### Database Configuration

```bash
DB_PATH=data/warehouse/climategpt.duckdb  # Database file path
DB_POOL_SIZE=10                            # Connection pool size (10-50)
DB_MAX_CONNECTIONS=20                      # Max concurrent connections
```

#### Performance Configuration

```bash
LLM_CONCURRENCY_LIMIT=10   # Max concurrent LLM calls (5-20)
CACHE_SIZE=1000            # Cache entry limit (500-5000)
CACHE_TTL_SECONDS=300      # Cache TTL in seconds (60-3600)
```

#### Security Configuration

```bash
ENVIRONMENT=production                     # production|development
ALLOWED_ORIGINS=https://example.com       # CORS whitelist (comma-separated)
RATE_LIMIT_MAX_REQUESTS=100               # Rate limit max (50-1000)
RATE_LIMIT_WINDOW_SECONDS=60              # Rate limit window (30-300)
```

#### Server Configuration

```bash
HTTP_HOST=0.0.0.0          # Bind address
HTTP_PORT=8010             # HTTP bridge port
```

### Environment-Specific Configurations

#### Development

```bash
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000
DB_POOL_SIZE=5
LLM_CONCURRENCY_LIMIT=5
CACHE_SIZE=500
RATE_LIMIT_MAX_REQUESTS=1000  # More lenient for testing
```

#### Staging

```bash
ENVIRONMENT=production
ALLOWED_ORIGINS=https://staging.example.com
DB_POOL_SIZE=10
LLM_CONCURRENCY_LIMIT=10
CACHE_SIZE=1000
RATE_LIMIT_MAX_REQUESTS=200
```

#### Production

```bash
ENVIRONMENT=production
ALLOWED_ORIGINS=https://climategpt.example.com
DB_POOL_SIZE=20
LLM_CONCURRENCY_LIMIT=15
CACHE_SIZE=2000
CACHE_TTL_SECONDS=600
RATE_LIMIT_MAX_REQUESTS=100
```

---

## Database Setup

### Initial Setup

#### 1. Download Database

```bash
# Create data directory
mkdir -p data/warehouse

# Option 1: Use existing database
cp /path/to/climategpt.duckdb data/warehouse/

# Option 2: Initialize empty database
python -c "import duckdb; duckdb.connect('data/warehouse/climategpt.duckdb')"
```

#### 2. Apply Indexes

```bash
# Run index creation script
python apply_database_indexes.py
```

**Expected output:**
```
DATABASE INDEX APPLICATION AND PERFORMANCE TESTING
================================================================================
STEP 1: MEASURING PERFORMANCE BEFORE INDEXING
...
STEP 2: CREATING INDEXES
✅ Indexes created successfully in 287.45 seconds (4.79 minutes)
...
AVERAGE SPEEDUP: 82.45x
```

#### 3. Create Materialized Views

```bash
# Run materialized view creation
python create_materialized_views.py
```

#### 4. Verify Setup

```bash
# Run validation
python validate_phase5.py
```

### Database Maintenance

#### Backup Database

```bash
# Full backup
cp data/warehouse/climategpt.duckdb data/warehouse/climategpt.duckdb.backup

# Compressed backup
tar -czf climategpt-backup-$(date +%Y%m%d).tar.gz data/warehouse/climategpt.duckdb
```

#### Restore Database

```bash
# From backup
cp data/warehouse/climategpt.duckdb.backup data/warehouse/climategpt.duckdb

# From compressed
tar -xzf climategpt-backup-20251116.tar.gz
```

#### Optimize Database

```python
import duckdb

conn = duckdb.connect("data/warehouse/climategpt.duckdb")

# Analyze tables for query optimization
conn.execute("ANALYZE")

# Vacuum to reclaim space
conn.execute("VACUUM")

conn.close()
```

---

## Monitoring and Logging

### Application Logs

#### View Logs

```bash
# Docker Compose
docker compose logs -f

# Kubernetes
kubectl logs -f deployment/climategpt-server -n climategpt

# Local
tail -f logs/climategpt.log
```

#### Log Format

```
[request-id] LEVEL - module - message

Example:
[a3d4f567-8901-2345-6789-abcdef012345] INFO - mcp_server - Query executed in 0.17ms
```

### Health Monitoring

#### Health Check Endpoint

```bash
curl http://localhost:8010/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.3.0",
  "uptime": 3600,
  "database": "connected",
  "cache_size": 432,
  "cache_hit_rate": 0.67
}
```

#### Metrics to Monitor

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| Response time | >100ms | Check database indexes |
| Error rate | >5% | Check logs, validate inputs |
| Cache hit rate | <40% | Increase cache size or TTL |
| Memory usage | >90% | Scale up or add replicas |
| CPU usage | >80% | Scale horizontally |
| Disk usage | >85% | Add storage or archive data |

---

## Troubleshooting

### Common Issues

#### Issue: Port Already in Use

**Symptoms:**
```
Error: Address already in use (8010)
```

**Solution:**
```bash
# Find process using port
lsof -ti:8010

# Kill process
kill -9 $(lsof -ti:8010)

# Or change port
export HTTP_PORT=8011
```

#### Issue: Database Connection Failed

**Symptoms:**
```
Error: Could not connect to database
```

**Solution:**
```bash
# Check database exists
ls -lh data/warehouse/climategpt.duckdb

# Check permissions
chmod 644 data/warehouse/climategpt.duckdb

# Verify database integrity
python -c "import duckdb; conn = duckdb.connect('data/warehouse/climategpt.duckdb'); print('OK')"
```

#### Issue: Out of Memory

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Reduce pool size
export DB_POOL_SIZE=5

# Reduce cache size
export CACHE_SIZE=500

# Restart with limits (Docker)
docker compose up -d --scale server=1
```

#### Issue: Slow Queries

**Symptoms:**
```
Query took 2000ms (expected <100ms)
```

**Solution:**
```bash
# Verify indexes exist
python -c "import duckdb; conn = duckdb.connect('data/warehouse/climategpt.duckdb'); print(conn.execute('SELECT COUNT(*) FROM duckdb_indexes()').fetchone())"

# Expected: 83+ indexes

# Re-run index creation if needed
python apply_database_indexes.py
```

#### Issue: Rate Limiting Too Strict

**Symptoms:**
```
429 Too Many Requests
```

**Solution:**
```bash
# Increase rate limit
export RATE_LIMIT_MAX_REQUESTS=500
export RATE_LIMIT_WINDOW_SECONDS=60

# Or disable for testing
export RATE_LIMIT_MAX_REQUESTS=999999
```

---

## Backup and Recovery

### Backup Strategy

#### Daily Backups

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR=/backups

# Create backup
tar -czf $BACKUP_DIR/climategpt-$DATE.tar.gz data/warehouse/climategpt.duckdb

# Remove backups older than 30 days
find $BACKUP_DIR -name "climategpt-*.tar.gz" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 cp $BACKUP_DIR/climategpt-$DATE.tar.gz s3://my-bucket/backups/
```

Add to cron:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

#### Kubernetes Backup

```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: climategpt-backup
  namespace: climategpt
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: climategpt:latest
            command:
            - /bin/bash
            - -c
            - |
              tar -czf /backups/climategpt-$(date +%Y%m%d).tar.gz /app/data/warehouse/climategpt.duckdb
            volumeMounts:
            - name: db-storage
              mountPath: /app/data
            - name: backup-storage
              mountPath: /backups
          restartPolicy: OnFailure
          volumes:
          - name: db-storage
            persistentVolumeClaim:
              claimName: climategpt-db-pvc
          - name: backup-storage
            persistentVolumeClaim:
              claimName: climategpt-backup-pvc
```

### Disaster Recovery

#### Recovery Procedure

1. **Stop application:**
   ```bash
   docker compose down
   # or
   kubectl scale deployment climategpt-server --replicas=0 -n climategpt
   ```

2. **Restore database:**
   ```bash
   tar -xzf climategpt-backup-20251116.tar.gz -C data/warehouse/
   ```

3. **Verify integrity:**
   ```bash
   python -c "import duckdb; conn = duckdb.connect('data/warehouse/climategpt.duckdb'); print(conn.execute('SELECT COUNT(*) FROM transport_country_year').fetchone())"
   ```

4. **Restart application:**
   ```bash
   docker compose up -d
   # or
   kubectl scale deployment climategpt-server --replicas=3 -n climategpt
   ```

5. **Verify health:**
   ```bash
   curl http://localhost:8010/health
   ```

---

## Security Hardening

### Production Checklist

- [ ] Use HTTPS/TLS (not HTTP)
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure explicit `ALLOWED_ORIGINS` (no wildcards)
- [ ] Use strong API credentials
- [ ] Enable rate limiting
- [ ] Restrict network access (firewall rules)
- [ ] Use secrets management (not environment variables in production)
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Implement monitoring and alerting

### Secrets Management

#### Using Docker Secrets

```bash
# Create secret
echo "username:password" | docker secret create openai_api_key -

# Update docker-compose.yml
services:
  server:
    secrets:
      - openai_api_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key

secrets:
  openai_api_key:
    external: true
```

#### Using Kubernetes Secrets

```bash
# Create from file
kubectl create secret generic climategpt-secrets \
  --from-file=OPENAI_API_KEY=./api-key.txt \
  -n climategpt

# Use in deployment
env:
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: climategpt-secrets
      key: OPENAI_API_KEY
```

---

## Performance Tuning

### Database Performance

```python
# utils/config.py

# For read-heavy workloads
DB_POOL_SIZE=20
DB_MAX_CONNECTIONS=50

# For balanced workloads
DB_POOL_SIZE=10
DB_MAX_CONNECTIONS=20

# For write-heavy workloads (not applicable for this read-only database)
DB_POOL_SIZE=5
DB_MAX_CONNECTIONS=10
```

### Application Performance

```bash
# High traffic production
LLM_CONCURRENCY_LIMIT=20
CACHE_SIZE=5000
CACHE_TTL_SECONDS=900

# Medium traffic
LLM_CONCURRENCY_LIMIT=10
CACHE_SIZE=2000
CACHE_TTL_SECONDS=600

# Low traffic / development
LLM_CONCURRENCY_LIMIT=5
CACHE_SIZE=500
CACHE_TTL_SECONDS=300
```

---

## Appendix

### Useful Commands

```bash
# Check application status
docker compose ps

# View resource usage
docker stats

# Check Kubernetes pod status
kubectl get pods -n climategpt -o wide

# Execute command in container
docker compose exec server bash
kubectl exec -it climategpt-server-xxx -n climategpt -- bash

# View environment variables
docker compose exec server env
kubectl exec climategpt-server-xxx -n climategpt -- env

# Run database query
docker compose exec server python -c "import duckdb; conn = duckdb.connect('data/warehouse/climategpt.duckdb'); print(conn.execute('SELECT COUNT(*) FROM transport_country_year').fetchone())"
```

### Support Resources

- **Documentation:** https://github.com/DharmpratapSingh/Team-1B-Fusion/tree/main/docs
- **Issues:** https://github.com/DharmpratapSingh/Team-1B-Fusion/issues
- **MCP Documentation:** https://modelcontextprotocol.io
- **DuckDB Documentation:** https://duckdb.org/docs

---

**Document Version:** 1.0.0
**Maintained By:** ClimateGPT Team
**Last Review:** 2025-11-16
