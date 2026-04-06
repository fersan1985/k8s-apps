# K8s Apps - GitOps Repository

This repository contains all Kubernetes applications and platform components managed by ArgoCD using professional patterns: **App of Apps**, **ApplicationSets**, and **Sync Waves**.

📖 **[Read PATTERNS.md](PATTERNS.md)** for detailed explanation of ArgoCD patterns used in this repo (QuickNode-style).

## Structure

```
.
├── argocd-apps/          # ArgoCD Application manifests
│   ├── keda.yaml
│   ├── docker-registry.yaml
│   └── meli-monitor.yaml
├── platform/             # Platform components (Helm values)
│   ├── keda/
│   └── ingress-nginx/
└── apps/                 # Application manifests
    ├── docker-registry/
    └── meli-monitor/
```

## Setup

### 1. Bootstrap ArgoCD

ArgoCD is the only component installed manually:

```bash
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/platform/argocd
./install.sh
```

Access: `http://192.168.0.34:30080`

Get password:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### 2. Add this Git Repository to ArgoCD

```bash
# Via CLI
argocd repo add https://github.com/fersan1985/k8s-apps.git

# Or via UI
Settings → Repositories → Connect Repo
```

### 3. Deploy Everything (App of Apps Pattern)

Deploy **ONE** application that manages all others:

```bash
cd ~/Documents/project/kubernetes/k8s-apps
kubectl apply -f argocd-apps/root-app.yaml
```

This will automatically create Applications for:
- ✅ KEDA (Wave 1 - Platform)
- ✅ docker-registry (Wave 2 - Apps)
- ✅ meli-monitor (Wave 2 - Apps)

**Alternative: Deploy individually (not recommended)**

```bash
kubectl apply -f argocd-apps/keda.yaml
kubectl apply -f argocd-apps/docker-registry.yaml
kubectl apply -f argocd-apps/meli-monitor.yaml
```

## Workflow

### Adding New Application

1. Create app directory: `apps/my-app/`
2. Add Kubernetes manifests or Helm chart values
3. Create ArgoCD Application: `argocd-apps/my-app.yaml`
4. Commit and push to Git
5. Apply Application manifest: `kubectl apply -f argocd-apps/my-app.yaml`
6. ArgoCD will automatically sync

### Updating Applications

1. Edit manifests/values in Git
2. Commit and push
3. ArgoCD auto-syncs (if enabled) or manual sync via UI/CLI

### Manual Sync

```bash
# Via CLI
argocd app sync keda

# Via UI
Click "Sync" button on application
```

## Platform Components

### KEDA (Event-Driven Autoscaling)

- **Version**: 2.13.1
- **Namespace**: `keda`
- **Manifest**: `argocd-apps/keda.yaml`
- **Values**: `platform/keda/values.yaml`

Features:
- Auto-scaling based on external metrics
- 50+ scalers (Kafka, Redis, Prometheus, Cron, etc.)
- Scale to zero capability

## Applications

### Docker Registry

Private Docker registry for homelab images.

- **Namespace**: `docker-registry`
- **Manifest**: `argocd-apps/docker-registry.yaml`

### Meli Monitor

Mercado Libre monitoring application.

- **Namespace**: `meli-monitor`
- **Manifest**: `argocd-apps/meli-monitor.yaml`

## Best Practices

1. **Never kubectl apply directly** - Always commit to Git and let ArgoCD sync
2. **Enable auto-sync** - For faster deployments
3. **Enable self-heal** - ArgoCD will revert manual changes
4. **Use prune** - Remove resources deleted from Git
5. **Version everything** - Pin Helm chart versions in Application manifests

## Troubleshooting

### Application Out of Sync

```bash
# Check differences
argocd app diff keda

# Force sync
argocd app sync keda --force
```

### Application Failed to Sync

```bash
# Check events
kubectl describe application keda -n argocd

# Check ArgoCD logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server
```

### Helm Chart Issues

```bash
# Validate Helm values
helm template kedacore/keda --version 2.13.1 -f platform/keda/values.yaml
```

## Resources

- [ArgoCD Docs](https://argo-cd.readthedocs.io/)
- [KEDA Docs](https://keda.sh/)
- [GitOps Principles](https://opengitops.dev/)
