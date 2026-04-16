# Prometheus & Grafana Stack

Stack completo de monitoreo con Prometheus y Grafana, desplegado vía ArgoCD.

**Configurado para:**
- ✅ kubernetes-mixin reglas y dashboards
- ✅ Reglas custom para namespaces de chains (`chain-*`)
- ✅ Exclusión de chains en alertas estándar de k8s
- ✅ Persistent storage con Rook-Ceph

## 🚀 Deployment con ArgoCD

### 1. Aplicar la Application

```bash
cd platform/prometheus-stack
kubectl apply -f application.yaml
```

### 2. Ver progreso en ArgoCD UI

```bash
# NodePort (tu setup)
https://192.168.0.34:30443

# O port-forward
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### 3. Sync manual (opcional)

```bash
# Via CLI
argocd app sync prometheus-stack

# Via UI
Applications → prometheus-stack → Sync
```

## 📁 Estructura

```
prometheus-stack/
├── application.yaml                # ArgoCD Application
├── values.yaml                     # Helm values (incluyendo chains config)
├── chain-prometheus-rules.yaml     # PrometheusRules custom
└── README.md
```

## 📊 Acceso a Servicios

### Grafana

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-stack-grafana 3000:80

# URL
http://localhost:3000

# Credentials
kubectl get secret -n monitoring prometheus-stack-grafana \
  -o jsonpath="{.data.admin-password}" | base64 -d
```

### Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-prometheus 9090:9090
# http://localhost:9090
```

### AlertManager

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-kube-prom-alertmanager 9093:9093
# http://localhost:9093
```

## 🔧 Configuración de Chains

### Namespaces Monitoreados

Ya configurados en `values.yaml`:
- `chain-ethereum`
- `chain-polygon`
- `chain-arbitrum`
- `chain-optimism`
- `chain-base`

### Agregar Más Chains

Editar `values.yaml` → `prometheus.prometheusSpec.additionalScrapeConfigs` y push al repo. ArgoCD auto-sync actualizará la config.

## 📋 Custom Rules para Chains

### Recording Rules

- `chain:pod_availability:ratio`
- `chain:container_restarts:rate15m`
- `chain:cpu_usage:sum`
- `chain:memory_usage:sum`

### Alertas

- **ChainPodsNotRunning**: Menos de 80% pods running
- **ChainHighRestartRate**: Reinicio frecuente
- **ChainPodCrashLooping**: Crash loops

### Aplicar Custom Rules

Las rules están en `chain-prometheus-rules.yaml`. Para aplicarlas:

```bash
kubectl apply -f chain-prometheus-rules.yaml
```

O mejor, integrarlas en ArgoCD (ver sección Advanced).

## ✅ Exclusión de Chains en K8s-Mixin Alerts

Las siguientes alertas de kubernetes-mixin **NO se disparan** para namespaces `chain-*`:

- KubePodCrashLooping
- KubePodNotReady
- KubeDeploymentReplicasMismatch
- KubeStatefulSetReplicasMismatch

Configurado en `chain-prometheus-rules.yaml` con override rules usando `namespace!~"chain-.*"`.

## 🧪 Testing

### 1. Crear Namespace de Chain

```bash
kubectl create namespace chain-ethereum
```

### 2. Deploy Test App

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eth-node
  namespace: chain-ethereum
spec:
  replicas: 1
  selector:
    matchLabels:
      app: eth-node
  template:
    metadata:
      labels:
        app: eth-node
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
    spec:
      containers:
      - name: eth-node
        image: nginx:alpine
```

### 3. Simular CrashLoop (test alerting)

```bash
kubectl run crash-test --image=busybox --namespace=chain-ethereum -- /bin/sh -c "exit 1"
```

Después de 5min verificar:
- ✅ Alerta `ChainPodCrashLooping` en AlertManager
- ❌ Alerta `KubePodCrashLooping` NO dispara (excluida)

### 4. Queries Útiles

```promql
# Pod availability
chain:pod_availability:ratio

# CPU por chain
chain:cpu_usage:sum

# Verificar exclusión
kube_pod_status_phase{namespace!~"chain-.*"}
```

## 🔄 Actualización

### Cambiar Versión del Chart

Editar `application.yaml`:

```yaml
spec:
  source:
    targetRevision: 65.2.0  # Nueva versión
```

Commit y push. ArgoCD auto-sync aplicará el cambio.

### Modificar Values

Editar `values.yaml`, commit, push. Auto-sync actualiza.

### Modificar Custom Rules

Opción 1 (manual):
```bash
kubectl apply -f chain-prometheus-rules.yaml
```

Opción 2 (GitOps): Mover a una App de ArgoCD separada.

## 🎨 Grafana Dashboards

### Dashboards Incluidos

- Kubernetes / Compute Resources / Cluster
- Kubernetes / Compute Resources / Namespace
- Kubernetes / Networking
- Node Exporter

### Dashboard Custom para Chains

En Grafana → Create → Dashboard, agregar paneles:

```promql
# Pod Availability
chain:pod_availability:ratio

# CPU Usage
chain:cpu_usage:sum

# Memory
chain:memory_usage:sum

# Restarts
chain:container_restarts:rate15m
```

## 🗑️ Cleanup

```bash
# Vía ArgoCD
kubectl delete -f application.yaml

# O manual
helm uninstall prometheus-stack -n monitoring
kubectl delete namespace monitoring
```

## 🔗 Advanced: GitOps Full

Para gestionar `chain-prometheus-rules.yaml` con ArgoCD:

### Opción A: Incluir en valores de Helm

Mover las rules a `values.yaml` → `prometheus.prometheusSpec.additionalPrometheusRulesMap`.

### Opción B: App separada

Crear `platform/prometheus-stack/rules/`:

```
rules/
├── application.yaml     # Otra ArgoCD App
└── chain-rules.yaml     # PrometheusRules
```

## 📚 Referencias

- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [kubernetes-mixin](https://github.com/kubernetes-monitoring/kubernetes-mixin)
- [ArgoCD Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
