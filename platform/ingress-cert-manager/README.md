# Cert-Manager

## Instalación con ArgoCD

```bash
# 1. Aplicar la Application de cert-manager
kubectl apply -f application.yaml

# 2. Aplicar los ClusterIssuers
kubectl apply -f cluster-issuer.yaml

# Verificar
kubectl get application -n argocd cert-manager
kubectl get pods -n cert-manager
kubectl get clusterissuer
```

## Uso en Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "selfsigned-issuer"
spec:
  tls:
  - hosts:
    - mi-app.home.local
    secretName: mi-app-tls
```

Cert-Manager creará el certificado automáticamente.
