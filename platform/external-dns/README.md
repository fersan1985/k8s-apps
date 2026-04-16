# ExternalDNS for AWS Route53

Sincroniza automáticamente registros DNS en Route53 desde recursos Ingress/Service de Kubernetes.

## Pre-requisitos

### 1. IAM User/Role en AWS

Crea un IAM User con permisos de Route53:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": [
        "arn:aws:route53:::hostedzone/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

### 2. Configurar credenciales AWS

```bash
# Copiar ejemplo
cp platform/external-dns/aws-credentials-secret.yaml.example platform/external-dns/aws-credentials-secret.yaml

# Editar con tus credenciales
# NO commitees este archivo a Git (está en .gitignore)
vim platform/external-dns/aws-credentials-secret.yaml

# Aplicar manualmente (solo una vez)
kubectl apply -f platform/external-dns/aws-credentials-secret.yaml
```

### 3. Verificar Hosted Zone en Route53

Asegúrate que la zona `sanchezcloud.com` existe en Route53.

## Instalación

ArgoCD sincronizará automáticamente desde GitHub:

```bash
# El root-app aplicará external-dns automáticamente
# Solo necesitas crear el Secret primero
kubectl apply -f platform/external-dns/aws-credentials-secret.yaml
```

## Uso

### Crear registro DNS automáticamente

Agrega la annotation `external-dns.alpha.kubernetes.io/hostname` a tu Ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-ingress
  namespace: argocd
  annotations:
    external-dns.alpha.kubernetes.io/hostname: argocd.sanchezcloud.com
spec:
  ingressClassName: nginx
  rules:
  - host: argocd.sanchezcloud.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 80
```

ExternalDNS creará automáticamente un registro A en Route53:
- `argocd.sanchezcloud.com` → IP del LoadBalancer (asignada por MetalLB)

### Verificación

```bash
# Ver logs de ExternalDNS
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns

# Verificar registros DNS creados
dig argocd.sanchezcloud.com
```

## Policy Modes

- **upsert-only**: Solo crea registros, no modifica ni elimina (modo seguro)
- **sync**: Crea, modifica y elimina registros (usa con precaución)

Por defecto está en `upsert-only`. Cambia a `sync` en `argocd-apps/external-dns.yaml` cuando estés seguro.

## Troubleshooting

### No se crean registros DNS

```bash
# Ver logs
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns

# Verificar permisos IAM
# Verificar que el Secret existe
kubectl get secret external-dns-aws -n external-dns

# Verificar que el Ingress tiene la annotation
kubectl get ingress -A -o yaml | grep external-dns
```

### Error de credenciales AWS

Verifica que las credenciales en el Secret sean correctas y tengan permisos suficientes.

## Referencias

- [ExternalDNS AWS Tutorial](https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md)
- [Route53 IAM Policy](https://github.com/kubernetes-sigs/external-dns/blob/master/docs/tutorials/aws.md#iam-policy)
