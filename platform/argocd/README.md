# ArgoCD - GitOps Continuous Deployment

ArgoCD is a declarative, GitOps continuous delivery tool for Kubernetes.

## Version

- **Helm Chart**: v6.7.3
- **ArgoCD**: v2.10.3
- **Installed**: 2026-04-06

## Installation

```bash
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/platform/argocd
chmod +x install.sh
./install.sh
```

## Access

### Via NodePort (Homelab)

```bash
# Get NodePorts
kubectl get svc -n argocd argocd-server

# Access
http://192.168.0.34:30080   # HTTP (any node IP)
https://192.168.0.34:30443  # HTTPS (any node IP)
```

### Initial Login

```bash
# Username
admin

# Password (get from secret)
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

### Change Password

```bash
# Option 1: Via CLI
argocd login <node-ip>:30443
argocd account update-password

# Option 2: Via UI
Settings → Account → Change Password
```

## Configuration

### values.yaml

Custom values for the Helm chart:

- **NodePort**: HTTP 30080, HTTPS 30443
- **Insecure**: Enabled (for homelab, no TLS required)
- **Resources**: CPU/Memory limits configured
- **ApplicationSet**: Enabled
- **Notifications**: Enabled

### Add Git Repository

```bash
# Via CLI
argocd repo add https://github.com/yourusername/your-repo.git

# Via UI
Settings → Repositories → Connect Repo
```

### Add Applications

Create an Application manifest:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/yourusername/your-repo.git
    targetRevision: HEAD
    path: apps/my-app
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Apply:

```bash
kubectl apply -f application.yaml
```

## Upgrade

```bash
# Update Helm repo
helm repo update

# Check new version
helm search repo argo/argo-cd

# Edit install.sh with new version
vim install.sh  # Change ARGOCD_VERSION

# Run upgrade
./install.sh
```

## Uninstall

```bash
helm uninstall argocd -n argocd
kubectl delete namespace argocd
```

## Useful Commands

```bash
# Check ArgoCD status
kubectl get pods -n argocd

# Get ArgoCD password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Port forward (alternative to NodePort)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# ArgoCD CLI login
argocd login <node-ip>:30443 --username admin

# List applications
argocd app list

# Sync application
argocd app sync my-app

# Get application details
argocd app get my-app
```

## Next Steps

1. Install ArgoCD CLI: `brew install argocd`
2. Add your Git repository with apps
3. Create Application CRs for your apps:
   - docker-registry
   - meli_monitor
4. Enable auto-sync for continuous deployment

## Resources

- [ArgoCD Docs](https://argo-cd.readthedocs.io/)
- [Helm Chart](https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd)
- [Best Practices](https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/)
