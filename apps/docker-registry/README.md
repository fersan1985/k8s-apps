# Docker Registry en Kubernetes

Registry privado de Docker para tu cluster RKE2.

## Deployment Rápido

```bash
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/apps/docker-registry

# Desplegar el registry
kubectl apply -f k8s/
```

## Configuración

### 1. Obtener la IP del nodo

```bash
kubectl get nodes -o wide
# Anotar la IP interna de algún nodo
```

### 2. Configurar RKE2 para usar el registry

En **cada nodo** del cluster, crear/editar:

`/etc/rancher/rke2/registries.yaml`:

```yaml
mirrors:
  "registry.local:5000":
    endpoint:
      - "http://NODE_IP:30500"

configs:
  "registry.local:5000":
    tls:
      insecure_skip_verify: true
```

Reemplazar `NODE_IP` con la IP del nodo donde corrió el comando anterior.

### 3. Reiniciar RKE2

```bash
# En cada nodo:
sudo systemctl restart rke2-server  # o rke2-agent si es worker
```

### 4. Configurar /etc/hosts (opcional)

En tu máquina local y en los nodos:

```bash
echo "NODE_IP registry.local" | sudo tee -a /etc/hosts
```

## Uso

### Desde tu máquina local

```bash
# Agregar registry inseguro a Docker Desktop
# En Settings → Docker Engine, agregar:
{
  "insecure-registries": ["registry.local:5000", "NODE_IP:30500"]
}

# Hacer build y push
docker build -t registry.local:5000/meli-monitor:latest .
docker push registry.local:5000/meli-monitor:latest
```

### Verificar imágenes

```bash
# Listar imágenes en el registry
curl http://NODE_IP:30500/v2/_catalog

# Ver tags de una imagen
curl http://NODE_IP:30500/v2/meli-monitor/tags/list
```

## Acceso via Ingress (opcional)

Si tenés un Ingress Controller instalado:

1. Editar `k8s/ingress.yaml` con tu dominio
2. Aplicar: `kubectl apply -f k8s/ingress.yaml`
3. Acceder via `registry.tudominio.com`

## Storage

- Por defecto usa 20Gi de storage persistente
- Ajustar en `k8s/pvc.yaml` según necesidades
- Cambiar `storageClassName` según tu cluster

## Limpieza

```bash
kubectl delete namespace docker-registry
```

## Troubleshooting

### Ver logs

```bash
kubectl logs -n docker-registry deployment/docker-registry -f
```

### Probar desde un pod

```bash
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- sh
# Dentro del pod:
curl http://docker-registry.docker-registry.svc.cluster.local:5000/v2/_catalog
```

### Error "http: server gave HTTP response to HTTPS client"

Asegurate de tener configurado el registry como inseguro en `/etc/rancher/rke2/registries.yaml`.
