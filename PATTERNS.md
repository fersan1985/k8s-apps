# ArgoCD Patterns - Professional GitOps

Este documento explica los patrones profesionales usados en este repositorio, similares a los que usan en QuickNode.

## Tabla de Contenidos

1. [App of Apps Pattern](#app-of-apps-pattern)
2. [ApplicationSets](#applicationsets)
3. [Sync Waves](#sync-waves)
4. [Comparación de Patrones](#comparación-de-patrones)

---

## App of Apps Pattern

### ¿Qué es?

Un patrón donde **una Application gestiona todas las demás Applications**. Es como el "root" de tu árbol de aplicaciones.

### Estructura

```
argocd-apps/
├── root-app.yaml           # ← La única que aplicas manualmente
├── keda.yaml              # ↓ Estas se crean automáticamente
├── docker-registry.yaml   # ↓ por root-app
└── meli-monitor.yaml      # ↓
```

### Deployment

```bash
# Solo necesitas aplicar UNA vez:
kubectl apply -f argocd-apps/root-app.yaml

# root-app detecta todos los YAML en argocd-apps/ y crea las Applications
```

### Ventajas

✅ **Single source of truth**: Un comando despliega todo
✅ **Declarativo**: Agregar nueva app = agregar YAML a Git
✅ **Self-managing**: ArgoCD gestiona sus propias Applications
✅ **Production-ready**: Usado en la mayoría de empresas

### Desventajas

❌ Si root-app falla, nada se despliega
❌ No genera apps dinámicamente (para eso usa ApplicationSets)

### Cómo Funciona

```yaml
# root-app.yaml
spec:
  source:
    path: argocd-apps        # Lee este directorio
    directory:
      recurse: false          # No subdirectorios
      exclude: root-app.yaml  # Evita recursión infinita
```

1. root-app mira `argocd-apps/` en Git
2. Encuentra: `keda.yaml`, `docker-registry.yaml`, `meli-monitor.yaml`
3. Crea 3 Applications en ArgoCD automáticamente
4. Cada Application se sincroniza con su source

### Uso en QuickNode

QuickNode usa este patrón con estructura:
```
apps/
├── root-app.yaml
├── production/
│   ├── ethereum-mainnet.yaml
│   ├── polygon-mainnet.yaml
│   └── solana-mainnet.yaml
└── staging/
    └── ethereum-sepolia.yaml
```

---

## ApplicationSets

### ¿Qué es?

Un **generador de Applications**. Define un template y una lista, y ArgoCD crea Applications automáticamente.

### Casos de Uso

1. **Multi-cluster**: Misma app en 10 clusters
2. **Multi-environment**: Misma app en dev/staging/prod
3. **Multi-region**: Misma app en us-east/eu-west/ap-south
4. **Dynamic discovery**: Genera apps desde directorios en Git

### Ejemplo: Platform Components

```yaml
# platform-appset.yaml
spec:
  generators:
    - list:
        elements:
          - component: keda
            version: "2.13.1"
          - component: ingress-nginx
            version: "4.9.0"
          - component: cert-manager
            version: "1.14.0"

  template:
    metadata:
      name: '{{component}}'  # Genera: keda, ingress-nginx, cert-manager
    spec:
      source:
        chart: '{{component}}'
        targetRevision: '{{version}}'
```

**Resultado**: 3 Applications creadas automáticamente

### Generators Disponibles

#### 1. List Generator (más simple)
```yaml
generators:
  - list:
      elements:
        - cluster: dev
          url: https://dev.k8s.local
        - cluster: prod
          url: https://prod.k8s.local
```

#### 2. Git Directory Generator (auto-discovery)
```yaml
generators:
  - git:
      repoURL: https://github.com/fersan1985/k8s-apps.git
      directories:
        - path: apps/*  # Crea app por cada directorio en apps/
```

#### 3. Git File Generator (desde JSON/YAML)
```yaml
generators:
  - git:
      repoURL: https://github.com/fersan1985/k8s-apps.git
      files:
        - path: config/clusters.json
```

`config/clusters.json`:
```json
[
  {"name": "cluster-1", "url": "https://cluster1.k8s.local"},
  {"name": "cluster-2", "url": "https://cluster2.k8s.local"}
]
```

#### 4. Cluster Generator (multi-cluster)
```yaml
generators:
  - clusters:
      selector:
        matchLabels:
          env: production  # Despliega en todos los clusters con esta label
```

### Progressive Rollout Strategy

ApplicationSets soportan rollouts graduales:

```yaml
spec:
  strategy:
    type: RollingSync
    rollingSync:
      steps:
        - matchExpressions:
            - key: env
              operator: In
              values: [dev]
        - matchExpressions:
            - key: env
              operator: In
              values: [staging]
        - matchExpressions:
            - key: env
              operator: In
              values: [prod]
```

**Resultado**: Despliega en dev → espera → staging → espera → prod

### Uso en QuickNode

QuickNode usa ApplicationSets para:
- **Multi-region blockchain nodes**: Misma config, 10 regiones
- **Per-customer tenants**: Genera namespace por cliente
- **Chain variants**: Mainnet/testnet con mismo template

Ejemplo (simplificado):
```yaml
generators:
  - list:
      elements:
        - chain: ethereum
          network: mainnet
          region: us-east-1
        - chain: ethereum
          network: mainnet
          region: eu-west-1
        - chain: polygon
          network: mainnet
          region: us-east-1
```

Genera: `ethereum-mainnet-us-east-1`, `ethereum-mainnet-eu-west-1`, etc.

---

## Sync Waves

### ¿Qué son?

Controlan el **orden de deployment** dentro de una Application. Kubernetes despliega recursos en paralelo por defecto, pero a veces necesitas orden específico.

### Sintaxis

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # Deploy en wave 1
```

### Orden de Ejecución

```
Wave -5  → Namespace, CRDs
  ↓
Wave 0   → Default (si no especificas wave)
  ↓
Wave 1   → Platform components (KEDA, Ingress)
  ↓
Wave 2   → Applications (docker-registry, meli-monitor)
  ↓
Wave 3   → Jobs, migrations
  ↓
Wave 10  → Post-install hooks
```

### Waves Negativas (Pre-install)

Usa waves negativas para recursos que deben existir ANTES:

```yaml
# Namespace primero
metadata:
  name: my-namespace
  annotations:
    argocd.argoproj.io/sync-wave: "-5"
---
# CRDs después
kind: CustomResourceDefinition
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-2"
---
# Apps al final
kind: Deployment
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"
```

### Ejemplo Real: Rook-Ceph

```yaml
# Wave -5: Namespace
apiVersion: v1
kind: Namespace
metadata:
  name: rook-ceph
  annotations:
    argocd.argoproj.io/sync-wave: "-5"

---
# Wave -2: CRDs
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: cephclusters.ceph.rook.io
  annotations:
    argocd.argoproj.io/sync-wave: "-2"

---
# Wave 0: Operator
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rook-ceph-operator
  annotations:
    argocd.argoproj.io/sync-wave: "0"

---
# Wave 2: CephCluster (usa el CRD)
apiVersion: ceph.rook.io/v1
kind: CephCluster
metadata:
  name: rook-ceph
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

### Sync Wave Hooks

Para ejecutar Jobs en waves específicas:

```yaml
# Wave 5: Migration job
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration
  annotations:
    argocd.argoproj.io/sync-wave: "5"
    argocd.argoproj.io/hook: Sync  # Run during sync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation  # Cleanup old jobs
spec:
  template:
    spec:
      containers:
        - name: migrate
          image: migrate/migrate
          command: ["migrate", "up"]
      restartPolicy: Never
```

### Waves en Applications (App of Apps)

También puedes usar waves en Applications para controlar orden entre apps:

```yaml
# KEDA primero (Wave 1)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: keda
  annotations:
    argocd.argoproj.io/sync-wave: "1"
---
# Apps después (Wave 2)
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: docker-registry
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

### Health Checks y Waves

ArgoCD espera que cada wave esté "Healthy" antes de continuar:

```
Wave 1 → Deploy → Wait for Healthy → Continue
Wave 2 → Deploy → Wait for Healthy → Continue
Wave 3 → Deploy → Wait for Healthy → Done
```

Si Wave 1 falla → Wave 2 nunca se despliega

### Uso en QuickNode

QuickNode usa waves para:

1. **Infrastructure**: `-5` → Namespaces, NetworkPolicies
2. **CRDs**: `-2` → Custom Resource Definitions
3. **Operators**: `0` → Prometheus Operator, Cert Manager
4. **Platform**: `1` → Monitoring, Logging
5. **Services**: `2` → Blockchain nodes, APIs
6. **Migrations**: `5` → Database migrations, one-time jobs

---

## Comparación de Patrones

### Individual Apps

**Cuándo usar:**
- ❌ Nunca en producción
- ✅ Testing rápido, demos

**Pros:**
- Simple, directo

**Cons:**
- No escala, manual, propenso a errores

```bash
kubectl apply -f app1.yaml
kubectl apply -f app2.yaml  # ¿Olvidaste alguna?
kubectl apply -f app3.yaml
```

---

### App of Apps

**Cuándo usar:**
- ✅ Producción (small-medium scale)
- ✅ Single cluster
- ✅ Estructura de apps conocida

**Pros:**
- Declarativo
- Single source of truth
- GitOps puro

**Cons:**
- No genera apps dinámicamente
- Requiere crear YAML por cada app

```bash
kubectl apply -f root-app.yaml  # ← ¡Una sola vez!
```

---

### ApplicationSets

**Cuándo usar:**
- ✅ Producción (medium-large scale)
- ✅ Multi-cluster
- ✅ Multi-environment
- ✅ Patrón repetitivo

**Pros:**
- DRY (Don't Repeat Yourself)
- Genera apps automáticamente
- Rollout strategies
- Multi-cluster support

**Cons:**
- Más complejo
- Debugging más difícil
- Overhead para casos simples

```bash
kubectl apply -f platform-appset.yaml  # ← Genera 10 apps
```

---

### Sync Waves

**Cuándo usar:**
- ✅ Siempre en producción
- ✅ Apps con dependencias
- ✅ CRDs + Operators
- ✅ Migrations

**Pros:**
- Control total del orden
- Previene race conditions
- Health checks entre waves

**Cons:**
- Deployment más lento (secuencial)
- Requiere planificación

---

## Patrón Recomendado (QuickNode-style)

Para homelab → producción:

```
1. Bootstrap (Manual):
   - ArgoCD installation

2. Root App (App of Apps):
   - argocd-apps/root-app.yaml
   - Gestiona ApplicationSets y Apps individuales

3. Platform (ApplicationSet):
   - platform-appset.yaml
   - Genera: KEDA, Ingress, Cert-Manager, etc.

4. Apps (Individual o AppSet según escala):
   - Individuales si < 10 apps
   - ApplicationSet si > 10 apps o multi-env

5. Waves en todo:
   - -5: Namespaces
   - -2: CRDs
   -  0: Operators
   -  1: Platform
   -  2: Apps
```

## Deployment Order

```
Manual Install
     ↓
 ArgoCD
     ↓
kubectl apply -f root-app.yaml
     ↓
Root App (Wave 0)
     ↓
┌────────────────────────────────┐
│  Platform AppSet (Wave 1)      │
│  Generates:                    │
│  - keda                        │
│  - ingress-nginx              │
│  - cert-manager               │
└────────────────────────────────┘
     ↓
┌────────────────────────────────┐
│  Apps (Wave 2)                 │
│  - docker-registry             │
│  - meli-monitor                │
└────────────────────────────────┘
```

## Testing

### Test App of Apps

```bash
# Apply root app
kubectl apply -f argocd-apps/root-app.yaml

# Watch Applications being created
kubectl get applications -n argocd -w

# Check sync status
argocd app list
```

### Test ApplicationSet

```bash
# Apply ApplicationSet
kubectl apply -f argocd-apps/platform-appset.yaml

# Watch generated Applications
kubectl get applicationset -n argocd
kubectl get applications -n argocd | grep platform-components
```

### Test Sync Waves

```bash
# Apply app with waves
kubectl apply -f argocd-apps/keda.yaml

# Watch sync progress (order by wave)
argocd app get keda --show-operation
```

## Resources

- [ArgoCD App of Apps](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)
- [ApplicationSets](https://argo-cd.readthedocs.io/en/stable/user-guide/application-set/)
- [Sync Waves](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [QuickNode Engineering Blog](https://quicknode.com/guides)
