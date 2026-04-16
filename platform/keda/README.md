# KEDA - Kubernetes Event-Driven Autoscaling

KEDA is a Kubernetes-based event-driven autoscaler that allows you to scale workloads based on external metrics.

## Version

- **Helm Chart**: v2.13.1
- **KEDA**: v2.13.1
- **Installed**: 2026-04-06

## Installation

```bash
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/platform/keda
chmod +x install.sh
./install.sh
```

## Features

KEDA enables event-driven autoscaling with support for:
- **50+ Scalers**: Kafka, Redis, RabbitMQ, Prometheus, Cron, HTTP, PostgreSQL, MySQL, etc.
- **Scale to Zero**: Scale workloads down to 0 replicas when idle
- **Custom Metrics**: Integrate with any event source via custom scalers
- **HPA Integration**: Works alongside Kubernetes Horizontal Pod Autoscaler

## Configuration

### values.yaml

Custom values for the Helm chart:

- **Operator**: Manages ScaledObject and ScaledJob resources
- **Metrics Server**: Exposes external metrics to HPA
- **Webhooks**: Validates KEDA resources
- **Prometheus Metrics**: Enabled on all components
- **Security**: Non-root containers with resource limits

## Basic Usage

### ScaledObject Example - Cron-based Scaling

Scale a deployment based on time schedule:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: my-deployment
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: cron
      metadata:
        timezone: America/New_York
        start: 0 8 * * *      # Scale up at 8 AM
        end: 0 18 * * *       # Scale down at 6 PM
        desiredReplicas: "5"
```

### ScaledObject Example - HTTP Requests

Scale based on incoming HTTP traffic:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: http-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: my-web-app
  minReplicaCount: 2
  maxReplicaCount: 20
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus:9090
        metricName: http_requests_per_second
        query: sum(rate(http_requests_total[2m]))
        threshold: '100'
```

### ScaledObject Example - Redis Queue

Scale based on Redis list length:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: redis-scaledobject
  namespace: default
spec:
  scaleTargetRef:
    name: worker-processor
  minReplicaCount: 1
  maxReplicaCount: 30
  triggers:
    - type: redis
      metadata:
        address: redis.default.svc.cluster.local:6379
        listName: job_queue
        listLength: "5"  # Scale up when queue > 5 items
```

### ScaledJob Example - Event Processing

Process jobs from a queue:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: job-processor
  namespace: default
spec:
  jobTargetRef:
    template:
      spec:
        containers:
          - name: processor
            image: my-job-processor:latest
        restartPolicy: Never
  pollingInterval: 30
  maxReplicaCount: 10
  successfulJobsHistoryLimit: 5
  failedJobsHistoryLimit: 5
  triggers:
    - type: rabbitmq
      metadata:
        host: amqp://rabbitmq.default.svc.cluster.local:5672
        queueName: tasks
        queueLength: '10'
```

## Common Scalers

### CPU/Memory Metrics

```yaml
triggers:
  - type: cpu
    metadata:
      type: Utilization
      value: "70"
  - type: memory
    metadata:
      type: Utilization
      value: "80"
```

### Prometheus Metrics

```yaml
triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus:9090
      metricName: custom_metric
      query: sum(my_metric{app="myapp"})
      threshold: '100'
```

### Kafka Topics

```yaml
triggers:
  - type: kafka
    metadata:
      bootstrapServers: kafka.default.svc.cluster.local:9092
      consumerGroup: my-consumer-group
      topic: events
      lagThreshold: '50'
```

### PostgreSQL Queue

```yaml
triggers:
  - type: postgresql
    metadata:
      host: postgres.default.svc.cluster.local
      port: "5432"
      userName: postgres
      passwordFromEnv: POSTGRES_PASSWORD
      dbName: mydb
      query: "SELECT COUNT(*) FROM jobs WHERE status = 'pending'"
      targetQueryValue: "10"
```

## Monitoring

### Check KEDA Status

```bash
# Check KEDA pods
kubectl get pods -n keda

# Check ScaledObjects
kubectl get scaledobject -A

# Check ScaledJobs
kubectl get scaledjob -A

# Describe ScaledObject
kubectl describe scaledobject <name> -n <namespace>
```

### KEDA Metrics

KEDA exposes Prometheus metrics on all components:

- **Operator**: `:8080/metrics`
- **Metrics Server**: `:9022/metrics`
- **Webhooks**: `:8080/metrics`

Example metrics:
- `keda_scaler_errors_total`
- `keda_scaled_object_errors`
- `keda_scaler_metrics_value`

### View HPA Created by KEDA

```bash
# KEDA creates HPA objects automatically
kubectl get hpa -A

# View HPA details
kubectl describe hpa keda-hpa-<scaledobject-name> -n <namespace>
```

## Troubleshooting

### ScaledObject Not Scaling

```bash
# Check ScaledObject events
kubectl describe scaledobject <name> -n <namespace>

# Check KEDA operator logs
kubectl logs -n keda -l app=keda-operator --tail=100

# Check metrics server logs
kubectl logs -n keda -l app=keda-metrics-apiserver --tail=100

# Verify external metric is available
kubectl get --raw /apis/external.metrics.k8s.io/v1beta1
```

### Authentication Issues

For scalers requiring authentication (Kafka, Redis, databases):

```yaml
# Create secret
apiVersion: v1
kind: Secret
metadata:
  name: kafka-credentials
  namespace: default
data:
  password: <base64-encoded-password>

# Reference in ScaledObject
triggers:
  - type: kafka
    metadata:
      # ... other config
    authenticationRef:
      name: kafka-auth

---
apiVersion: keda.sh/v1alpha1
kind: TriggerAuthentication
metadata:
  name: kafka-auth
  namespace: default
spec:
  secretTargetRef:
    - parameter: password
      name: kafka-credentials
      key: password
```

## Upgrade

```bash
# Update Helm repo
helm repo update

# Check new version
helm search repo kedacore/keda

# Edit install.sh with new version
vim install.sh  # Change KEDA_VERSION

# Run upgrade
./install.sh
```

## Uninstall

```bash
# Delete all ScaledObjects first
kubectl delete scaledobject --all -A

# Uninstall KEDA
helm uninstall keda -n keda
kubectl delete namespace keda

# Clean up CRDs (optional)
kubectl delete crd scaledobjects.keda.sh
kubectl delete crd scaledjobs.keda.sh
kubectl delete crd triggerauthentications.keda.sh
kubectl delete crd clustertriggerauthentications.keda.sh
```

## Use Cases for Homelab

### 1. Scale Docker Registry Cleaner

Run cleanup job when storage is high:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledJob
metadata:
  name: registry-cleaner
  namespace: docker-registry
spec:
  jobTargetRef:
    template:
      spec:
        containers:
          - name: cleaner
            image: registry-cleaner:latest
        restartPolicy: OnFailure
  triggers:
    - type: cron
      metadata:
        timezone: America/New_York
        start: 0 2 * * *  # Run at 2 AM daily
        end: 0 3 * * *
        desiredReplicas: "1"
```

### 2. Scale API Based on Load

For your meli_monitor API:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: meli-monitor-scaler
  namespace: meli-monitor
spec:
  scaleTargetRef:
    name: meli-monitor-api
  minReplicaCount: 1
  maxReplicaCount: 5
  triggers:
    - type: cpu
      metadata:
        type: Utilization
        value: "70"
```

### 3. Process Background Jobs

Scale workers based on queue depth:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: background-workers
  namespace: default
spec:
  scaleTargetRef:
    name: workers
  minReplicaCount: 0  # Scale to zero when idle
  maxReplicaCount: 10
  triggers:
    - type: redis
      metadata:
        address: redis:6379
        listName: jobs
        listLength: "3"
```

## Resources

- [KEDA Docs](https://keda.sh/docs/)
- [Scalers Reference](https://keda.sh/docs/scalers/)
- [Helm Chart](https://github.com/kedacore/charts)
- [Examples](https://github.com/kedacore/samples)

## Next Steps

1. Deploy a test ScaledObject to verify KEDA is working
2. Integrate with Prometheus for custom metrics
3. Create ScaledObjects for your applications:
   - docker-registry: Cron-based cleanup jobs
   - meli_monitor: CPU/Memory-based scaling
