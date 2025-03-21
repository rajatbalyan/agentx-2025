# Deployment Guide

This guide covers the deployment of AgentX in various environments, from local development to production.

## Docker Deployment

### Prerequisites

- Docker
- Docker Compose
- Git

### Building the Image

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agentx.git
cd agentx
```

2. Build the Docker image:
```bash
docker-compose build
```

3. Start the services:
```bash
docker-compose up -d
```

### Docker Compose Configuration

The `docker-compose.yml` file defines all services:

```yaml
version: '3.8'

services:
  agentx:
    build: .
    ports:
      - "8000-8007:8000-8007"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_REPO=${GITHUB_REPO}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
      - prometheus
      - grafana

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus

volumes:
  redis_data:
  prometheus_data:
  grafana_data:
```

### Environment Variables

Create a `.env` file with required variables:

```env
# API Keys
GOOGLE_API_KEY=your_google_api_key_here
GITHUB_TOKEN=your_github_token_here

# Website Configuration
TARGET_WEBSITE=https://example.com
SCAN_INTERVAL=3600

# Agent Configuration
MANAGER_AGENT_PORT=8000
READ_AGENT_PORT=8001
CONTENT_UPDATE_AGENT_PORT=8002
SEO_OPTIMIZATION_AGENT_PORT=8003
ERROR_FIXING_AGENT_PORT=8004
CONTENT_GENERATION_AGENT_PORT=8005
PERFORMANCE_MONITORING_AGENT_PORT=8006
CICD_DEPLOYMENT_AGENT_PORT=8007

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/agentx.log

# Memory Configuration
MEMORY_PATH=/app/data/memory
VECTOR_STORE_PATH=/app/data/memory/vectors
CONVERSATION_STORE_PATH=/app/data/memory/conversations

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_PASSWORD=admin

# Model Paths
SEO_MODEL_PATH=/app/models/seo_agent/
CONTENT_GEN_MODEL_PATH=/app/models/content_gen/
ERROR_FIX_MODEL_PATH=/app/models/error_fix/

# GitHub Configuration
GITHUB_REPO=owner/repo
GITHUB_BRANCH=main
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster
- kubectl
- Helm (optional)

### Using Helm

1. Add the Helm repository:
```bash
helm repo add agentx https://yourusername.github.io/agentx
helm repo update
```

2. Install AgentX:
```bash
helm install agentx agentx/agentx \
  --namespace agentx \
  --create-namespace \
  --set googleApiKey=your_key \
  --set githubToken=your_token
```

### Manual Deployment

1. Create namespace:
```bash
kubectl create namespace agentx
```

2. Create ConfigMap:
```bash
kubectl create configmap agentx-config \
  --from-file=agentx.config.yaml \
  --namespace agentx
```

3. Create Secret:
```bash
kubectl create secret generic agentx-secrets \
  --from-literal=google-api-key=your_key \
  --from-literal=github-token=your_token \
  --namespace agentx
```

4. Deploy services:
```bash
kubectl apply -f k8s/
```

### Kubernetes Resources

#### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentx
  namespace: agentx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agentx
  template:
    metadata:
      labels:
        app: agentx
    spec:
      containers:
      - name: agentx
        image: yourusername/agentx:latest
        ports:
        - containerPort: 8000
          name: manager
        - containerPort: 8001
          name: read
        - containerPort: 8002
          name: content-update
        - containerPort: 8003
          name: seo
        - containerPort: 8004
          name: error-fixing
        - containerPort: 8005
          name: content-generation
        - containerPort: 8006
          name: performance
        - containerPort: 8007
          name: cicd
        envFrom:
        - configMapRef:
            name: agentx-config
        - secretRef:
            name: agentx-secrets
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: agentx-data
      - name: logs
        persistentVolumeClaim:
          claimName: agentx-logs
```

#### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentx
  namespace: agentx
spec:
  selector:
    app: agentx
  ports:
  - name: manager
    port: 8000
    targetPort: 8000
  - name: read
    port: 8001
    targetPort: 8001
  - name: content-update
    port: 8002
    targetPort: 8002
  - name: seo
    port: 8003
    targetPort: 8003
  - name: error-fixing
    port: 8004
    targetPort: 8004
  - name: content-generation
    port: 8005
    targetPort: 8005
  - name: performance
    port: 8006
    targetPort: 8006
  - name: cicd
    port: 8007
    targetPort: 8007
```

#### PersistentVolume

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: agentx-data
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /data/agentx
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agentx-data
  namespace: agentx
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## Monitoring and Logging

### Prometheus Configuration

The `prometheus.yml` file configures metrics collection:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agentx'
    static_configs:
      - targets: ['agentx:8000']
        labels:
          agent: 'manager'
      - targets: ['agentx:8001']
        labels:
          agent: 'read'
      # ... other agents ...

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Grafana Dashboards

1. Access Grafana at `http://localhost:3000`
2. Default credentials:
   - Username: admin
   - Password: admin

3. Import dashboards:
   - System Overview
   - Agent Metrics
   - Performance Metrics

## Scaling

### Horizontal Scaling

1. Update deployment replicas:
```bash
kubectl scale deployment agentx --replicas=3 -n agentx
```

2. Configure load balancing:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentx
spec:
  type: LoadBalancer
  # ... other configurations ...
```

### Resource Limits

1. Set resource requests and limits:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

2. Configure auto-scaling:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agentx
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentx
  minReplicas: 1
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Security Considerations

1. **API Key Management**
   - Use Kubernetes secrets
   - Rotate keys regularly
   - Limit key permissions

2. **Network Security**
   - Use internal networks
   - Configure firewalls
   - Enable TLS

3. **Access Control**
   - Use RBAC
   - Implement authentication
   - Monitor access logs

4. **Data Security**
   - Encrypt sensitive data
   - Regular backups
   - Access auditing

## Maintenance

### Updates

1. Update image:
```bash
kubectl set image deployment/agentx agentx=yourusername/agentx:new-version -n agentx
```

2. Rollback if needed:
```bash
kubectl rollout undo deployment/agentx -n agentx
```

### Monitoring

1. Check pod status:
```bash
kubectl get pods -n agentx
```

2. View logs:
```bash
kubectl logs -f deployment/agentx -n agentx
```

3. Monitor metrics:
```bash
kubectl port-forward svc/prometheus 9090:9090 -n agentx
```

### Backup and Recovery

1. Backup data:
```bash
kubectl exec -it deployment/agentx -n agentx -- tar czf /backup/data.tar.gz /app/data
```

2. Restore data:
```bash
kubectl cp data.tar.gz deployment/agentx:/app/data -n agentx
kubectl exec -it deployment/agentx -n agentx -- tar xzf /app/data/data.tar.gz
``` 