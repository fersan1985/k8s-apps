# Nginx Ingress Controller

## Instalación con ArgoCD

```bash
# Aplicar la Application
kubectl apply -f application.yaml

# Verificar
kubectl get application -n argocd ingress-nginx
kubectl get pods -n ingress-nginx
```

## Acceso

Con NodePort configurado:
- HTTP: Puerto `30080`
- HTTPS: Puerto `30443`

**Ejemplo:** `https://argocd.home.local:30443`

## Configuración

Edita `application.yaml` para cambiar valores. ArgoCD sincronizará automáticamente.

### Cambiar a LoadBalancer (con MetalLB)

Edita `application.yaml`:

```yaml
valuesObject:
  controller:
    service:
      type: LoadBalancer
      loadBalancerIP: "192.168.0.50"
```

Luego ArgoCD sincronizará automáticamente.
