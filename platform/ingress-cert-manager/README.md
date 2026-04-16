# Cert-Manager con Let's Encrypt + Route53

Gestión automática de certificados SSL/TLS usando Let's Encrypt con DNS-01 challenge.

## Pre-requisitos

### 1. IAM User/Role en AWS

El mismo IAM User de ExternalDNS sirve (necesita permisos de Route53).

### 2. Configurar credenciales AWS

```bash
# Copiar ejemplo
cp platform/ingress-cert-manager/aws-credentials-secret.yaml.example \
   platform/ingress-cert-manager/aws-credentials-secret.yaml

# Editar con tu AWS Secret Access Key
vim platform/ingress-cert-manager/aws-credentials-secret.yaml

# Aplicar manualmente (solo una vez)
kubectl apply -f platform/ingress-cert-manager/aws-credentials-secret.yaml
```

### 3. Configurar ClusterIssuer

Edita `platform/ingress-cert-manager/cluster-issuer-letsencrypt.yaml`:

```yaml
email: tu-email@example.com  # Para notificaciones de Let's Encrypt
accessKeyID: AKIAXXXXXXXXXXXXXXXX  # Tu AWS Access Key ID
region: us-east-1  # Tu región de AWS
```

## Instalación

```bash
# 1. Crear Secret con credenciales AWS
kubectl apply -f platform/ingress-cert-manager/aws-credentials-secret.yaml

# 2. ArgoCD sincronizará automáticamente cert-manager y ClusterIssuers
```

## Uso

### Testing con Staging (IMPORTANTE: Hazlo primero)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-staging"  # Staging primero
    external-dns.alpha.kubernetes.io/hostname: test.cloudsanchez.com
spec:
  tls:
  - hosts:
    - test.cloudsanchez.com
    secretName: test-tls
```

Verifica que funciona:

```bash
# Ver estado del certificado
kubectl get certificate -n <namespace>
kubectl describe certificate test-tls -n <namespace>

# Ver logs de cert-manager
kubectl logs -n cert-manager -l app=cert-manager

# Verificar DNS
dig test.cloudsanchez.com
```

### Producción con Let's Encrypt Production

Una vez que staging funciona, cambia a production:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"  # Production
    external-dns.alpha.kubernetes.io/hostname: argocd.cloudsanchez.com
spec:
  tls:
  - hosts:
    - argocd.cloudsanchez.com
    secretName: argocd-cloudsanchez-tls
```

## Flujo completo

1. **MetalLB** asigna IP fija (ej: 192.168.0.50) al Ingress Controller
2. **ExternalDNS** crea registro A en Route53: `argocd.cloudsanchez.com` → `192.168.0.50`
3. **Cert-Manager** solicita certificado a Let's Encrypt usando DNS-01 challenge:
   - Let's Encrypt pide validar dominio via DNS
   - Cert-Manager crea registro TXT en Route53
   - Let's Encrypt valida y emite certificado
   - Cert-Manager guarda certificado en Secret
4. **Nginx Ingress** usa el certificado para servir HTTPS

## Verificación

```bash
# Ver certificados
kubectl get certificate -A

# Ver detalles de un certificado
kubectl describe certificate argocd-cloudsanchez-tls -n argocd

# Ver logs de cert-manager
kubectl logs -n cert-manager -l app=cert-manager --tail=50

# Probar HTTPS
curl -I https://argocd.cloudsanchez.com

# Verificar certificado SSL
openssl s_client -connect argocd.cloudsanchez.com:443 -servername argocd.cloudsanchez.com
```

## Troubleshooting

### Certificado no se genera

```bash
# Ver estado
kubectl describe certificate <name> -n <namespace>

# Ver CertificateRequest
kubectl get certificaterequest -n <namespace>

# Ver logs de cert-manager
kubectl logs -n cert-manager -l app=cert-manager | grep -i error
```

**Causas comunes:**
1. Credenciales AWS incorrectas o sin permisos
2. Registro DNS no se creó (verificar ExternalDNS)
3. Email o accessKeyID no configurado en ClusterIssuer
4. Rate limit de Let's Encrypt (usa staging primero)

### Rate Limits de Let's Encrypt

Let's Encrypt tiene límites:
- 50 certificados por dominio/semana
- 5 fallos de validación por cuenta/hora

**Solución**: Usa `letsencrypt-staging` para testing.

## Referencias

- [Cert-Manager AWS Route53](https://cert-manager.io/docs/configuration/acme/dns01/route53/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
