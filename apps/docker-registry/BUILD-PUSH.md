# Docker Registry - Build & Push Workflow

Este documento explica cómo usar el Docker Registry privado en el cluster para tus aplicaciones.

## Arquitectura

```
Developer Machine
     │
     │ docker build + docker push
     ▼
Docker Registry (NodePort 30500)
     │
     │ Pull images
     ▼
Kubernetes Pods (meli-monitor, etc.)
```

## Acceso al Registry

### Interno (desde pods en el cluster)
```
docker-registry.docker-registry.svc.cluster.local:5000
```

### Externo (desde tu máquina)
```
192.168.0.34:30500  # O cualquier IP del cluster
```

## Configuración de Docker

### 1. Marcar Registry como Insecure

El registry no usa HTTPS (homelab), necesitas configurar Docker:

**Mac/Linux** - Edita `/etc/docker/daemon.json`:
```json
{
  "insecure-registries": [
    "192.168.0.34:30500",
    "192.168.0.35:30500",
    "192.168.0.38:30500",
    "192.168.0.123:30500"
  ]
}
```

**Restart Docker:**
```bash
sudo systemctl restart docker  # Linux
# Mac: Restart Docker Desktop
```

### 2. Verificar Conectividad

```bash
curl http://192.168.0.34:30500/v2/_catalog
# Debería retornar: {"repositories":[]}
```

## Build & Push: Meli Monitor

### Paso 1: Build la imagen

```bash
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/apps/meli_monitor

# Build con tag para registry privado
docker build -t 192.168.0.34:30500/meli-monitor:latest .
```

### Paso 2: Push al Registry

```bash
docker push 192.168.0.34:30500/meli-monitor:latest
```

### Paso 3: Verificar Push

```bash
# Listar imágenes en registry
curl http://192.168.0.34:30500/v2/_catalog

# Ver tags de meli-monitor
curl http://192.168.0.34:30500/v2/meli-monitor/tags/list
```

**Output esperado:**
```json
{
  "name": "meli-monitor",
  "tags": ["latest"]
}
```

## Workflow Completo

### Initial Build & Deploy

```bash
# 1. Build imagen
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/apps/meli_monitor
docker build -t 192.168.0.34:30500/meli-monitor:latest .

# 2. Push a registry
docker push 192.168.0.34:30500/meli-monitor:latest

# 3. Deploy via ArgoCD (si no está deployado)
kubectl apply -f ~/Documents/project/kubernetes/k8s-apps/argocd-apps/root-app.yaml

# ArgoCD desplegará:
# Wave 1: KEDA
# Wave 2: Docker Registry
# Wave 3: Meli Monitor (que pull de docker-registry)
```

### Update Image (Desarrollo)

```bash
# 1. Hacer cambios en código
vim mercadolibre_monitor.py

# 2. Rebuild con nuevo tag
docker build -t 192.168.0.34:30500/meli-monitor:v1.1.0 .

# 3. Push nuevo tag
docker push 192.168.0.34:30500/meli-monitor:v1.1.0

# 4. Actualizar values.yaml en Git
cd ~/Documents/project/kubernetes/k8s-apps
vim apps/meli_monitor/helm/values.yaml
# Cambiar: tag: "v1.1.0"

# 5. Commit y push
git add apps/meli_monitor/helm/values.yaml
git commit -m "Update meli-monitor to v1.1.0"
git push origin main

# 6. ArgoCD auto-sync (o manual)
argocd app sync meli-monitor
```

## Tagging Strategy

### Development
```bash
docker build -t 192.168.0.34:30500/meli-monitor:dev .
docker push 192.168.0.34:30500/meli-monitor:dev
```

### Staging
```bash
docker build -t 192.168.0.34:30500/meli-monitor:staging-$(date +%Y%m%d) .
docker push 192.168.0.34:30500/meli-monitor:staging-20260406
```

### Production
```bash
docker build -t 192.168.0.34:30500/meli-monitor:v1.0.0 .
docker push 192.168.0.34:30500/meli-monitor:v1.0.0

# También tag como latest
docker tag 192.168.0.34:30500/meli-monitor:v1.0.0 192.168.0.34:30500/meli-monitor:latest
docker push 192.168.0.34:30500/meli-monitor:latest
```

## Multi-arch Builds (Opcional)

Si tu cluster tiene arquitecturas mixtas (amd64 + arm64):

```bash
# Build para múltiples arquitecturas
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t 192.168.0.34:30500/meli-monitor:latest \
  --push .
```

## Troubleshooting

### Error: "http: server gave HTTP response to HTTPS client"

**Causa:** Docker intenta usar HTTPS pero registry es HTTP

**Solución:** Agrega registry a `insecure-registries` en `/etc/docker/daemon.json`

### Error: "connection refused"

**Causa:** NodePort no accesible

**Verificar:**
```bash
# Check registry pod
kubectl get pods -n docker-registry

# Check service
kubectl get svc -n docker-registry

# Test desde nodo
ssh ubuntu@192.168.0.34 'curl http://localhost:30500/v2/'
```

### Error: "manifest unknown"

**Causa:** Imagen no existe en registry

**Verificar:**
```bash
curl http://192.168.0.34:30500/v2/_catalog
curl http://192.168.0.34:30500/v2/meli-monitor/tags/list
```

### Pod "ImagePullBackOff"

**Causa:** Kubernetes no puede pullear imagen

**Debug:**
```bash
# Describe pod
kubectl describe pod <pod-name> -n meli-monitor

# Check events
kubectl get events -n meli-monitor --sort-by='.lastTimestamp'

# Verificar que imagen existe
curl http://docker-registry.docker-registry.svc.cluster.local:5000/v2/meli-monitor/tags/list
```

**Solución común:** Agregar `imagePullSecrets` (si registry requiere auth, pero en este caso es público)

## Registry Storage

El registry usa **Rook-Ceph** para almacenamiento persistente:

- **StorageClass:** `rook-ceph-block`
- **Capacity:** 20Gi
- **Backup:** Las imágenes persisten incluso si el pod se reinicia

### Verificar Storage

```bash
# Check PVC
kubectl get pvc -n docker-registry

# Check usage
kubectl exec -n docker-registry deployment/docker-registry -- du -sh /var/lib/registry
```

## Cleanup

### Delete Specific Image

```bash
# Registry UI no soporta delete, usa registry API:
curl -X DELETE http://192.168.0.34:30500/v2/meli-monitor/manifests/<digest>

# Luego garbage collect
kubectl exec -n docker-registry deployment/docker-registry -- \
  /bin/registry garbage-collect /etc/docker/registry/config.yml
```

### Limpiar Cache Local

```bash
docker image rm 192.168.0.34:30500/meli-monitor:latest
docker system prune -a
```

## CI/CD Integration (Futuro)

Cuando uses CI/CD (GitHub Actions, GitLab CI):

```yaml
# .github/workflows/build.yml
- name: Build and push to registry
  run: |
    docker build -t 192.168.0.34:30500/meli-monitor:${{ github.sha }} .
    docker push 192.168.0.34:30500/meli-monitor:${{ github.sha }}
```

## Resources

- [Docker Registry Docs](https://docs.docker.com/registry/)
- [Registry Configuration](https://docs.docker.com/registry/configuration/)
- [Docker Insecure Registries](https://docs.docker.com/registry/insecure/)
