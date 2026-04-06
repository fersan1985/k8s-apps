# GitOps Deployment Guide

Complete guide to deploy the entire platform using GitOps with ArgoCD.

## Prerequisites

- RKE2 cluster running (1 CP + 2 workers + 1 storage)
- Rook-Ceph storage deployed
- kubectl configured with cluster access
- Helm 3.x installed

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   RKE2 Cluster                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  ArgoCD (Bootstrap - Manual Install)          │  │
│  │  - Watches: github.com/fersan1985/k8s-apps   │  │
│  │  - NodePort: 30080 (HTTP), 30443 (HTTPS)     │  │
│  └──────────────────────────────────────────────┘  │
│                        │                             │
│                        ▼                             │
│  ┌──────────────────────────────────────────────┐  │
│  │  Platform Components (GitOps)                 │  │
│  │  - KEDA (Event-driven autoscaling)           │  │
│  │  - Ingress-NGINX (Future)                    │  │
│  └──────────────────────────────────────────────┘  │
│                        │                             │
│                        ▼                             │
│  ┌──────────────────────────────────────────────┐  │
│  │  Applications (GitOps)                        │  │
│  │  - docker-registry                            │  │
│  │  - meli-monitor                               │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Step 1: Bootstrap ArgoCD (Manual)

ArgoCD is the **only** component installed manually. Everything else is managed by ArgoCD.

```bash
# Navigate to ArgoCD install directory
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/platform/argocd

# Install ArgoCD via Helm
export KUBECONFIG=~/.kube/rke2-cluster-config
./install.sh
```

**Wait** for all ArgoCD pods to be ready (this may take 5-10 minutes):

```bash
kubectl get pods -n argocd -w
```

Expected output when ready:
```
NAME                                  READY   STATUS    RESTARTS   AGE
argocd-application-controller-0       1/1     Running   0          5m
argocd-applicationset-controller-*    1/1     Running   0          5m
argocd-dex-server-*                   1/1     Running   0          5m
argocd-notifications-controller-*     1/1     Running   0          5m
argocd-redis-*                        1/1     Running   0          5m
argocd-repo-server-*                  1/1     Running   0          5m
argocd-server-*                       1/1     Running   0          5m
```

## Step 2: Access ArgoCD UI

### Get NodePort

```bash
kubectl get svc -n argocd argocd-server
```

### Access via Browser

```
http://192.168.0.34:30080    # Any node IP works
```

### Login Credentials

**Username:** `admin`

**Password:**
```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

### Change Password (Recommended)

```bash
# Install ArgoCD CLI (Mac)
brew install argocd

# Login
argocd login 192.168.0.34:30080 --username admin --insecure

# Change password
argocd account update-password
```

## Step 3: Add Git Repository to ArgoCD

### Via CLI

```bash
argocd repo add https://github.com/fersan1985/k8s-apps.git
```

### Via UI

1. Go to **Settings** → **Repositories**
2. Click **Connect Repo**
3. Choose **Via HTTPS**
4. Enter:
   - Repository URL: `https://github.com/fersan1985/k8s-apps.git`
   - Leave other fields empty (public repo)
5. Click **Connect**

## Step 4: Deploy Platform Components

Deploy KEDA first (required for autoscaling):

```bash
cd ~/Documents/project/kubernetes/k8s-apps

# Deploy KEDA via ArgoCD
kubectl apply -f argocd-apps/keda.yaml
```

**Verify in ArgoCD UI:**
- Go to **Applications**
- You should see `keda` appearing
- Click on it to see deployment progress
- Wait for "Synced" and "Healthy" status

**Verify via kubectl:**
```bash
kubectl get pods -n keda
```

Expected:
```
NAME                                READY   STATUS    RESTARTS   AGE
keda-operator-*                     1/1     Running   0          2m
keda-operator-metrics-apiserver-*   1/1     Running   0          2m
keda-admission-webhooks-*           1/1     Running   0          2m
```

## Step 5: Deploy Applications

### Deploy Docker Registry

```bash
kubectl apply -f argocd-apps/docker-registry.yaml
```

**Verify:**
```bash
kubectl get pods -n docker-registry
```

### Deploy Meli Monitor

```bash
kubectl apply -f argocd-apps/meli-monitor.yaml
```

**Verify:**
```bash
kubectl get pods -n meli-monitor
kubectl get cronjob -n meli-monitor
```

## Step 6: Verify Everything

```bash
# Check all ArgoCD applications
argocd app list

# Expected output:
# NAME              CLUSTER                         NAMESPACE       PROJECT  STATUS  HEALTH   SYNCPOLICY  CONDITIONS
# docker-registry   https://kubernetes.default.svc  docker-registry default  Synced  Healthy  Auto-Prune  <none>
# keda              https://kubernetes.default.svc  keda            default  Synced  Healthy  Auto-Prune  <none>
# meli-monitor      https://kubernetes.default.svc  meli-monitor    default  Synced  Healthy  Auto-Prune  <none>
```

## GitOps Workflow

### Making Changes

1. **Edit files** in `k8s-apps` repository:
   ```bash
   cd ~/Documents/project/kubernetes/k8s-apps
   vim apps/docker-registry/k8s/deployment.yaml
   ```

2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Update docker-registry deployment"
   git push origin main
   ```

3. **ArgoCD auto-syncs** (within 3 minutes)
   - Or click "Sync" in UI for immediate sync
   - Or run: `argocd app sync docker-registry`

### Adding New Application

1. **Create app directory:**
   ```bash
   mkdir -p apps/my-new-app/k8s
   ```

2. **Add Kubernetes manifests:**
   ```bash
   cat > apps/my-new-app/k8s/deployment.yaml <<EOF
   apiVersion: apps/v1
   kind: Deployment
   ...
   EOF
   ```

3. **Create ArgoCD Application:**
   ```bash
   cat > argocd-apps/my-new-app.yaml <<EOF
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: my-new-app
     namespace: argocd
   spec:
     project: default
     source:
       repoURL: https://github.com/fersan1985/k8s-apps.git
       targetRevision: HEAD
       path: apps/my-new-app/k8s
     destination:
       server: https://kubernetes.default.svc
       namespace: my-new-app
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
       syncOptions:
         - CreateNamespace=true
   EOF
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add my-new-app"
   git push origin main
   ```

5. **Deploy via ArgoCD:**
   ```bash
   kubectl apply -f argocd-apps/my-new-app.yaml
   ```

## Troubleshooting

### Application Stuck in "Progressing"

```bash
# Check app details
argocd app get <app-name>

# Check events
kubectl describe application <app-name> -n argocd

# Force sync
argocd app sync <app-name> --force
```

### Application "Out of Sync"

```bash
# See differences between Git and cluster
argocd app diff <app-name>

# Sync
argocd app sync <app-name>
```

### Pod Issues

```bash
# Check pod logs
kubectl logs -n <namespace> <pod-name>

# Describe pod
kubectl describe pod -n <namespace> <pod-name>

# Check PVC if storage issues
kubectl get pvc -n <namespace>
kubectl describe pvc -n <namespace> <pvc-name>
```

### ArgoCD UI Not Accessible

```bash
# Check ArgoCD pods
kubectl get pods -n argocd

# Check service
kubectl get svc -n argocd argocd-server

# Port forward as alternative
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Access: https://localhost:8080
```

## Maintenance

### Update Platform Component (KEDA)

```bash
cd ~/Documents/project/kubernetes/k8s-apps

# Edit version in Application manifest
vim argocd-apps/keda.yaml
# Change targetRevision: 2.13.1 → 2.14.0

# Commit and push
git add argocd-apps/keda.yaml
git commit -m "Upgrade KEDA to 2.14.0"
git push origin main

# ArgoCD will auto-sync (or manual sync)
argocd app sync keda
```

### Rollback Application

```bash
# Via UI: Click "History and Rollback" → Select revision → Rollback

# Via CLI:
argocd app rollback <app-name> <revision-id>
```

### Delete Application

```bash
# Delete from cluster (ArgoCD will remove all resources)
kubectl delete -f argocd-apps/<app-name>.yaml

# Or via CLI
argocd app delete <app-name>
```

## Best Practices

1. ✅ **Never `kubectl apply` directly** - Always commit to Git first
2. ✅ **Enable auto-sync** - Faster deployments, self-healing
3. ✅ **Enable prune** - Clean up deleted resources
4. ✅ **Pin versions** - Explicit chart/image versions in Git
5. ✅ **Use namespaces** - One namespace per app
6. ✅ **Test in branch** - Use Git branches for testing changes
7. ✅ **Monitor ArgoCD UI** - Check sync status regularly
8. ✅ **Document changes** - Good commit messages

## Next Steps

- [ ] Deploy Ingress-NGINX for external access
- [ ] Add Prometheus + Grafana for monitoring
- [ ] Set up ArgoCD notifications (Slack/Email)
- [ ] Create KEDA ScaledObjects for apps
- [ ] Add cert-manager for TLS certificates
- [ ] Set up automated backups with Velero

## Resources

- **Repository**: https://github.com/fersan1985/k8s-apps
- **ArgoCD UI**: http://192.168.0.34:30080
- **ArgoCD Docs**: https://argo-cd.readthedocs.io/
- **KEDA Docs**: https://keda.sh/
