# Setup Guide - Complete Platform Stack

Guía completa para desplegar el stack de plataforma con GitOps.

## Arquitectura

```
┌─────────────────────┐
│   sanchezcloud.com  │  (Route53 - AWS)
│   DNS Zone          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   ExternalDNS       │  Sincroniza Ingress → Route53
│                     │  argocd.sanchezcloud.com → 192.168.0.50
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│   MetalLB           │  Asigna IP fija 192.168.0.50
│   LoadBalancer      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Ingress-Nginx      │  Reverse Proxy (puerto 80/443)
│  (RKE2 Built-in)    │
└──────────┬──────────┘
           │
    ┌──────┴──────┬──────────┬──────────┐
    ▼             ▼          ▼          ▼
┌────────┐   ┌────────┐  ┌────────┐  ┌────────┐
│ ArgoCD │   │Grafana │  │Registry│  │  App   │
└────────┘   └────────┘  └────────┘  └────────┘

┌─────────────────────┐
│  Cert-Manager       │  Certificados SSL de Let's Encrypt
│  + Let's Encrypt    │  DNS-01 Challenge via Route53
└─────────────────────┘
```

## Pre-requisitos

### 1. AWS Setup

#### a. Route53 Hosted Zone
- Crea una Hosted Zone para `sanchezcloud.com` en Route53
- Anota el Hosted Zone ID

#### b. IAM User con permisos
Crea un IAM User con esta policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "arn:aws:route53:::hostedzone/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:GetChange"
      ],
      "Resource": "*"
    }
  ]
}
```

Genera Access Key y Secret Access Key.

### 2. Kubernetes Cluster

- RKE2 cluster funcionando
- `kubectl` configurado
- ArgoCD instalado

### 3. Red Local

- Rango de IPs disponibles para MetalLB (ej: `192.168.0.50-192.168.0.60`)
- Estas IPs NO deben estar en uso por DHCP

## Instalación Paso a Paso

### Paso 1: Configurar Credenciales AWS

```bash
# 1. ExternalDNS credentials
cp platform/external-dns/aws-credentials-secret.yaml.example \
   platform/external-dns/aws-credentials-secret.yaml

# Editar con tus credenciales
vim platform/external-dns/aws-credentials-secret.yaml

# Aplicar
kubectl apply -f platform/external-dns/aws-credentials-secret.yaml

# 2. Cert-Manager credentials (mismo AWS user)
cp platform/ingress-cert-manager/aws-credentials-secret.yaml.example \
   platform/ingress-cert-manager/aws-credentials-secret.yaml

# Editar
vim platform/ingress-cert-manager/aws-credentials-secret.yaml

# Aplicar
kubectl apply -f platform/ingress-cert-manager/aws-credentials-secret.yaml
```

### Paso 2: Configurar ClusterIssuer

Edita `platform/ingress-cert-manager/cluster-issuer-letsencrypt.yaml`:

```yaml
email: tu-email@example.com  # Cambia esto
accessKeyID: AKIAXXXXXXXX    # Tu AWS Access Key ID
region: us-east-1            # Tu región AWS
```

### Paso 3: Ajustar IP Pool de MetalLB

Edita `platform/metallb/ipaddresspool.yaml`:

```yaml
addresses:
- 192.168.0.50-192.168.0.60  # Ajusta según tu red
```

### Paso 4: Commit y Push

```bash
cd /path/to/k8s-apps
git add .
git commit -m "Configure platform stack with MetalLB, ExternalDNS, and Let's Encrypt"
git push
```

### Paso 5: ArgoCD Sincroniza Automáticamente

El `root-app` detectará los cambios y desplegará en orden:

1. **Wave 1**: MetalLB
2. **Wave 2**: MetalLB Config (IP Pool)
3. **Wave 3**: ExternalDNS + Cert-Manager
4. **Wave 4**: ClusterIssuers
5. **Wave 5**: Ingress de aplicaciones

Verifica el progreso:

```bash
# Ver applications
kubectl get applications -n argocd

# Ver pods
kubectl get pods -A

# Ver servicios con LoadBalancer
kubectl get svc -A | grep LoadBalancer
```

### Paso 6: Actualizar Ingress de ArgoCD

Reemplaza `platform/argocd/ingress.yaml` con `ingress-letsencrypt.yaml`:

```bash
cd platform/argocd
mv ingress.yaml ingress-old.yaml
mv ingress-letsencrypt.yaml ingress.yaml

# Commit y push
git add .
git commit -m "Update ArgoCD ingress to use Let's Encrypt and ExternalDNS"
git push
```

ArgoCD sincronizará y:
1. MetalLB asignará IP 192.168.0.50 al Ingress Controller
2. ExternalDNS creará `argocd.sanchezcloud.com → 192.168.0.50` en Route53
3. Cert-Manager solicitará certificado SSL de Let's Encrypt
4. Let's Encrypt validará vía DNS-01 challenge
5. Certificado válido listo!

## Verificación

### 1. MetalLB

```bash
# Ver IP asignada al Ingress
kubectl get svc -n kube-system | grep ingress

# Debería mostrar algo como:
# rke2-ingress-nginx-controller  LoadBalancer  10.43.x.x  192.168.0.50  80:xxx,443:xxx
```

### 2. ExternalDNS

```bash
# Ver logs
kubectl logs -n external-dns -l app.kubernetes.io/name=external-dns

# Verificar DNS (desde Route53 o usando dig)
dig argocd.sanchezcloud.com

# Debería devolver: 192.168.0.50
```

### 3. Cert-Manager

```bash
# Ver certificados
kubectl get certificate -A

# Ver detalles
kubectl describe certificate argocd-sanchezcloud-tls -n argocd

# Debería mostrar: Ready = True
```

### 4. Acceso HTTPS

```bash
# Desde tu navegador
https://argocd.sanchezcloud.com

# Debería:
# - Cargar ArgoCD sin warning de certificado
# - Mostrar certificado emitido por Let's Encrypt
# - Candado verde en el navegador
```

## Agregar Nuevas Aplicaciones

### Ejemplo: Grafana

```yaml
# apps/grafana/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: monitoring
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    external-dns.alpha.kubernetes.io/hostname: grafana.sanchezcloud.com
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - grafana.sanchezcloud.com
    secretName: grafana-sanchezcloud-tls
  rules:
  - host: grafana.sanchezcloud.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: grafana
            port:
              number: 80
```

Commit, push, y automáticamente tendrás:
- DNS: `grafana.sanchezcloud.com → 192.168.0.50`
- SSL: Certificado válido de Let's Encrypt
- Acceso: `https://grafana.sanchezcloud.com`

## Troubleshooting

Ver los READMEs individuales:
- `platform/metallb/README.md` (si lo creamos)
- `platform/external-dns/README.md`
- `platform/ingress-cert-manager/README.md`

## Rate Limits de Let's Encrypt

**IMPORTANTE**: Usa `letsencrypt-staging` primero para testing!

Let's Encrypt tiene límites:
- 50 certificados/semana por dominio
- 5 fallos de validación/hora

Para testing:
```yaml
cert-manager.io/cluster-issuer: "letsencrypt-staging"
```

Para producción (después de verificar que staging funciona):
```yaml
cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

## Acceso desde Internet (Opcional)

Si quieres acceso desde internet:

1. **Port Forwarding en router**:
   - Puerto 80 → 192.168.0.50:80
   - Puerto 443 → 192.168.0.50:443

2. **IP Pública en Route53**:
   - Cambia ExternalDNS o actualiza manualmente los registros A para usar tu IP pública

3. **Seguridad**:
   - Considera VPN (Tailscale, Wireguard)
   - OAuth2 Proxy para autenticación centralizada
   - Fail2ban para protección contra brute force
