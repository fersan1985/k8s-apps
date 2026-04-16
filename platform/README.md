# Platform Components

Componentes de plataforma para el cluster RKE2, gestionados con Helm.

## Estructura

```
platform/
├── argocd/              # GitOps CD tool
│   ├── values.yaml      # Custom values
│   ├── install.sh       # Installation script
│   └── README.md
│
├── keda/                # Event-driven autoscaling
│   ├── values.yaml
│   ├── install.sh
│   └── README.md
│
└── ingress-nginx/       # Ingress controller
    ├── values.yaml
    ├── install.sh
    └── README.md
```

## Installation Order

1. **Ingress Nginx** - Acceso externo HTTP/HTTPS
2. **ArgoCD** - GitOps continuous deployment
3. **KEDA** - Event-driven autoscaling

## Quick Start

```bash
# 1. Ingress Controller
cd ingress-nginx
./install.sh

# 2. ArgoCD
cd ../argocd
./install.sh

# 3. KEDA
cd ../keda
./install.sh
```

## Access

Después de instalar, verificar accesos:

```bash
# ArgoCD UI
kubectl get svc -n argocd argocd-server

# Ingress Controller
kubectl get svc -n ingress-nginx
```

## Version Management

Todas las versiones están especificadas en los scripts de instalación para reproducibilidad.

Para actualizar una versión:
1. Editar `install.sh` con la nueva versión
2. Ejecutar el script
3. Commit el cambio al repo

## Helm Repositories

```bash
# ArgoCD
helm repo add argo https://argoproj.github.io/argo-helm

# KEDA
helm repo add kedacore https://kedacore.github.io/charts

# Ingress Nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx

# Update all
helm repo update
```
