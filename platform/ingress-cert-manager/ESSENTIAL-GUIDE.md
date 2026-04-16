# Ingress + Cert-Manager - URLs con SSL Automático

## 🎯 Objetivo Final

Pasar de esto:
```
http://192.168.0.34:30080  (feo, no SSL, puerto raro)
```

A esto:
```
https://argocd.home.local   (bonito, SSL, puerto 443)
https://registry.home.local
https://monitor.home.local
```

---

## 📚 Conceptos Core

### 1. ¿Qué es un Ingress?

**Ingress** = Puerta de entrada HTTP/HTTPS a tu cluster

**Sin Ingress:**
```
Usuario → NodePort:30080 → Service → Pod
Usuario → NodePort:30443 → Service → Pod
Usuario → NodePort:31234 → Service → Pod
```
❌ Un puerto diferente por cada app

**Con Ingress:**
```
Usuario → :443 (HTTPS) → Ingress Controller
                            ├─ argocd.home.local → ArgoCD Service → Pods
                            ├─ registry.home.local → Registry Service → Pods
                            └─ monitor.home.local → Monitor Service → Pods
```
✅ Un solo puerto (443), múltiples apps por dominio

### 2. ¿Qué es Cert-Manager?

**Cert-Manager** = Robot que gestiona certificados SSL automáticamente

**Sin Cert-Manager:**
1. Generas cert manualmente con `openssl`
2. Lo guardas en un Secret
3. Lo referencias en el Ingress
4. **Expira en 90 días** → Repites 1-4 manualmente ⚠️

**Con Cert-Manager:**
1. Defines un `Certificate` CRD
2. Cert-Manager lo genera automáticamente
3. **Auto-renueva antes de expirar** ✅

---

## 🏗️ Arquitectura completa

```
┌─────────────────┐
│  Tu navegador   │
└────────┬────────┘
         │ https://argocd.home.local
         ▼
┌─────────────────┐
│   Pi-hole DNS   │ argocd.home.local → 192.168.0.34
└────────┬────────┘
         ▼
┌─────────────────┐
│ Nginx Ingress   │ :443 (LoadBalancer o NodePort)
│   Controller    │
└────────┬────────┘
         │
         ├─ Host: argocd.home.local ──→ argocd-server Service → Pods
         ├─ Host: registry.home.local → docker-registry Service → Pods
         └─ Host: monitor.home.local ──→ meli-monitor Service → Pods

┌─────────────────┐
│  Cert-Manager   │ (genera + renueva SSL certs)
└─────────────────┘
```

---

## 🚀 Setup Paso a Paso

### Paso 1: Instalar Nginx Ingress Controller

```bash
# Agregar repo de Helm
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Instalar con valores custom
cat > ingress-nginx-values.yaml <<EOF
controller:
  service:
    type: LoadBalancer  # Si tienes MetalLB
    # type: NodePort    # Si NO tienes MetalLB
    loadBalancerIP: "192.168.0.50"  # IP fija para Ingress

  # Opcional: NodePort fijo (si usas NodePort en vez de LoadBalancer)
  # service:
  #   nodePorts:
  #     http: 30080
  #     https: 30443

  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 256Mi
EOF

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values ingress-nginx-values.yaml
```

**Verificar:**
```bash
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx

# Si usas LoadBalancer, debería mostrar:
# ingress-nginx-controller  LoadBalancer  192.168.0.50  80:xxxxx/TCP,443:xxxxx/TCP
```

### Paso 2: Instalar Cert-Manager

```bash
# Agregar repo
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Instalar CRDs primero
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.14.0/cert-manager.crds.yaml

# Instalar Cert-Manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.14.0
```

**Verificar:**
```bash
kubectl get pods -n cert-manager

# Debería mostrar 3 pods running:
# cert-manager-xxxxx
# cert-manager-cainjector-xxxxx
# cert-manager-webhook-xxxxx
```

### Paso 3: Configurar ClusterIssuer (Self-Signed para homelab)

Para homelab, usamos certificados **self-signed** (autofirmados). Para producción usarías Let's Encrypt.

```yaml
# cluster-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
---
# CA Issuer (opcional, para firmar con tu propia CA)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: ca-issuer
spec:
  ca:
    secretName: ca-key-pair
```

**Aplicar:**
```bash
kubectl apply -f cluster-issuer.yaml

# Verificar
kubectl get clusterissuer
```

### Paso 4: Configurar DNS Local (Pi-hole)

En Pi-hole, agregar **Local DNS Records**:

```
Settings → Local DNS → DNS Records

argocd.home.local     → 192.168.0.50
registry.home.local   → 192.168.0.50
monitor.home.local    → 192.168.0.50
*.home.local          → 192.168.0.50  (wildcard)
```

**Test:**
```bash
dig argocd.home.local  # Debería devolver 192.168.0.50
ping argocd.home.local
```

---

## 📝 Crear Ingress para una app

### Ejemplo: ArgoCD

```yaml
# argocd-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: argocd-ingress
  namespace: argocd
  annotations:
    cert-manager.io/cluster-issuer: "selfsigned-issuer"
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"  # ArgoCD maneja su propio SSL
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - argocd.home.local
    secretName: argocd-tls  # Cert-Manager creará este Secret
  rules:
  - host: argocd.home.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: argocd-server
            port:
              number: 443
```

**Aplicar:**
```bash
kubectl apply -f argocd-ingress.yaml

# Ver el Ingress
kubectl get ingress -n argocd
kubectl describe ingress argocd-ingress -n argocd

# Ver el certificado generado
kubectl get certificate -n argocd
kubectl describe certificate argocd-tls -n argocd
```

**Acceder:**
```bash
# En tu navegador
https://argocd.home.local

# Si el navegador se queja del cert self-signed:
# Chrome: "Advanced" → "Proceed to argocd.home.local (unsafe)"
# Firefox: "Advanced" → "Accept the Risk and Continue"
```

### Ejemplo: Docker Registry

```yaml
# docker-registry-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: docker-registry-ingress
  namespace: docker-registry
  annotations:
    cert-manager.io/cluster-issuer: "selfsigned-issuer"
    nginx.ingress.kubernetes.io/proxy-body-size: "0"  # Sin límite de tamaño (para images grandes)
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - registry.home.local
    secretName: registry-tls
  rules:
  - host: registry.home.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: docker-registry
            port:
              number: 5000
```

**Aplicar y testear:**
```bash
kubectl apply -f docker-registry-ingress.yaml

# Test desde Docker
docker login registry.home.local
docker tag mi-imagen:latest registry.home.local/mi-imagen:latest
docker push registry.home.local/mi-imagen:latest
```

---

## 🔐 Certificados: Self-Signed vs Let's Encrypt

### Self-Signed (Recomendado para homelab)

**Pros:**
- ✅ Gratis, ilimitado
- ✅ Funciona sin internet
- ✅ No requiere dominio público
- ✅ Perfecto para red interna

**Contras:**
- ❌ Navegador muestra warning (debes aceptar manualmente)
- ❌ No sirve para acceso público

**Configuración:**
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
```

### Let's Encrypt (Para producción/acceso externo)

**Pros:**
- ✅ Cert válido (sin warnings en navegador)
- ✅ Gratis
- ✅ Renovación automática

**Contras:**
- ❌ Requiere dominio público
- ❌ Requiere que port 80/443 sea accesible desde internet
- ❌ Rate limits (50 certs/semana)

**Configuración:**
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: tu-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

**Cuándo usar cada uno:**

| Escenario | Issuer recomendado |
|-----------|-------------------|
| Apps internas (*.home.local) | Self-Signed |
| Exposición pública (tudominio.com) | Let's Encrypt |
| Desarrollo local | Self-Signed |
| Cliente externo va a acceder | Let's Encrypt |

---

## 🐛 Troubleshooting

### Ingress creado pero no accesible

**Diagnóstico:**
```bash
# Ver Ingress
kubectl get ingress -n <namespace>
kubectl describe ingress <name> -n <namespace>

# Ver logs del Ingress Controller
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Test DNS
dig argocd.home.local
ping 192.168.0.50
```

**Causas comunes:**
1. DNS no apunta a la IP del Ingress Controller
2. Service backend no existe o está mal
3. IngressClassName incorrecto

### Certificado no se genera

**Diagnóstico:**
```bash
# Ver Certificates
kubectl get certificate -n <namespace>
kubectl describe certificate <name> -n <namespace>

# Ver CertificateRequests
kubectl get certificaterequest -n <namespace>

# Ver logs de Cert-Manager
kubectl logs -n cert-manager -l app=cert-manager
```

**Causas comunes:**
1. ClusterIssuer no existe
2. Annotation `cert-manager.io/cluster-issuer` mal escrita
3. Secret name duplicado

### Warning en navegador (self-signed)

**Normal para self-signed certs.** Opciones:

1. **Aceptar el riesgo manualmente** (OK para homelab)
2. **Importar el CA cert en tu navegador:**
   ```bash
   # Obtener el CA cert
   kubectl get secret -n <namespace> <secretName> -o jsonpath='{.data.ca\.crt}' | base64 -d > ca.crt

   # Importar en:
   # - Chrome: Settings → Security → Manage Certificates
   # - Firefox: Preferences → Privacy & Security → Certificates → View Certificates
   ```

---

## 📋 Template reutilizable

Para agregar una nueva app con Ingress + SSL:

```yaml
---
# 1. Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: NOMBRE-APP-ingress
  namespace: NAMESPACE
  annotations:
    cert-manager.io/cluster-issuer: "selfsigned-issuer"
    # nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"  # Si el backend es HTTPS
    # nginx.ingress.kubernetes.io/proxy-body-size: "0"       # Sin límite de body (uploads)
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - NOMBRE-APP.home.local
    secretName: NOMBRE-APP-tls
  rules:
  - host: NOMBRE-APP.home.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: NOMBRE-SERVICE
            port:
              number: PUERTO
```

**Pasos:**
1. Reemplaza `NOMBRE-APP`, `NAMESPACE`, `NOMBRE-SERVICE`, `PUERTO`
2. Aplica: `kubectl apply -f ingress.yaml`
3. Agrega DNS en Pi-hole: `NOMBRE-APP.home.local → 192.168.0.50`
4. Accede: `https://NOMBRE-APP.home.local`

---

## 🎓 Workflow completo

### Agregar nueva app con URL personalizada

```bash
# 1. Deploy la app (via ArgoCD o kubectl)
kubectl apply -f app-deployment.yaml

# 2. Crear Service (si no existe)
kubectl expose deployment mi-app --port=80 --target-port=8080 -n mi-app

# 3. Crear Ingress
cat > ingress.yaml <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mi-app-ingress
  namespace: mi-app
  annotations:
    cert-manager.io/cluster-issuer: "selfsigned-issuer"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - mi-app.home.local
    secretName: mi-app-tls
  rules:
  - host: mi-app.home.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mi-app
            port:
              number: 80
EOF

kubectl apply -f ingress.yaml

# 4. Agregar DNS en Pi-hole
# UI: Settings → Local DNS → DNS Records
# mi-app.home.local → 192.168.0.50

# 5. Verificar
kubectl get ingress -n mi-app
kubectl get certificate -n mi-app
curl -k https://mi-app.home.local  # -k para ignorar self-signed warning

# 6. Acceder desde navegador
open https://mi-app.home.local
```

---

## ✅ Checklist de dominio

Dominas Ingress + Cert-Manager cuando puedes:

- [ ] Instalar Nginx Ingress Controller
- [ ] Instalar Cert-Manager
- [ ] Crear un ClusterIssuer (self-signed)
- [ ] Crear un Ingress para exponer una app con HTTPS
- [ ] Configurar DNS local (Pi-hole) para apuntar a Ingress
- [ ] Entender la diferencia entre self-signed y Let's Encrypt
- [ ] Troubleshootear un Certificate que no se genera
- [ ] Agregar una nueva app con su propia URL en <5 minutos

**Si puedes hacer esto, dominas el 80% de Ingress + SSL en K8s.**

---

## 📚 Referencias

- **Nginx Ingress**: https://kubernetes.github.io/ingress-nginx/
- **Cert-Manager**: https://cert-manager.io/docs/
- **Let's Encrypt**: https://letsencrypt.org/
- **Ingress API**: https://kubernetes.io/docs/concepts/services-networking/ingress/

---

## 🎯 Siguiente paso

Una vez que domines esto, considera:

1. **Wildcard certificates** - Un cert para `*.home.local`
2. **OAuth2 Proxy** - Autenticación centralizada para todas las apps
3. **External DNS** - Sincronizar Ingress → DNS automáticamente
4. **Rate limiting** - Proteger tus apps de abuso
