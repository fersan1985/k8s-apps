# Deployment en Kubernetes (RKE2)

Guía para desplegar el monitor de MercadoLibre en tu cluster RKE2.

## Pre-requisitos

- Cluster RKE2 funcionando
- `kubectl` configurado
- Docker o Podman para construir la imagen
- (Opcional) Registry privado o Docker Hub account

## 1. Construir la imagen Docker

```bash
# Construir la imagen
docker build -t mercadolibre-monitor:latest .

# Si usás un registry privado, taggeá y pushea:
docker tag mercadolibre-monitor:latest your-registry.com/mercadolibre-monitor:latest
docker push your-registry.com/mercadolibre-monitor:latest
```

Para RKE2, también podés importar la imagen directamente:

```bash
# Guardar imagen
docker save mercadolibre-monitor:latest | gzip > mercadolibre-monitor.tar.gz

# Copiar a nodo del cluster e importar
scp mercadolibre-monitor.tar.gz node:/tmp/
ssh node "sudo k3s ctr images import /tmp/mercadolibre-monitor.tar.gz"
```

## 2. Configurar notificaciones (opcional)

### Opción A: Slack

1. Crear un webhook en Slack: https://api.slack.com/messaging/webhooks
2. Crear el secret:

```bash
kubectl create secret generic notification-secrets \
  --from-literal=slack-webhook='https://hooks.slack.com/services/YOUR/WEBHOOK/URL' \
  -n mercadolibre-monitor
```

### Opción B: Discord

1. Crear un webhook en Discord (Server Settings → Integrations → Webhooks)
2. Crear el secret:

```bash
kubectl create secret generic notification-secrets \
  --from-literal=discord-webhook='https://discord.com/api/webhooks/YOUR/WEBHOOK/URL' \
  -n mercadolibre-monitor
```

### Opción C: Ambos

```bash
kubectl create secret generic notification-secrets \
  --from-literal=slack-webhook='https://hooks.slack.com/services/...' \
  --from-literal=discord-webhook='https://discord.com/api/webhooks/...' \
  -n mercadolibre-monitor
```

## 3. Configurar productos a monitorear

Editá `k8s/configmap.yaml` y agregá las URLs de los productos:

```yaml
data:
  products.txt: |
    https://www.mercadolibre.com.ar/producto1/...
    https://www.mercadolibre.com.ar/producto2/...
```

## 4. Desplegar en Kubernetes

```bash
# Aplicar todos los manifiestos
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/cronjob.yaml
```

## 5. Verificar el deployment

```bash
# Ver el cronjob
kubectl get cronjob -n mercadolibre-monitor

# Ver jobs ejecutados
kubectl get jobs -n mercadolibre-monitor

# Ver logs del último job
kubectl logs -n mercadolibre-monitor job/mercadolibre-monitor-<timestamp>

# Ver el PVC
kubectl get pvc -n mercadolibre-monitor
```

## 6. Ejecutar manualmente (testing)

```bash
# Crear un job manual desde el cronjob
kubectl create job -n mercadolibre-monitor \
  --from=cronjob/mercadolibre-monitor \
  test-run

# Ver logs
kubectl logs -n mercadolibre-monitor job/test-run -f
```

## 7. Agregar productos manualmente

```bash
# Crear un pod temporal para agregar productos
kubectl run -n mercadolibre-monitor -it --rm add-product \
  --image=mercadolibre-monitor:latest \
  --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"add-product","image":"mercadolibre-monitor:latest","command":["python","mercadolibre_monitor.py","add","https://www.mercadolibre.com.ar/..."],"volumeMounts":[{"name":"data","mountPath":"/data"}],"env":[{"name":"DATA_FILE","value":"/data/.mercadolibre_monitor.json"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"mercadolibre-data"}}]}}'
```

## Configuración del CronJob

Por defecto, el CronJob ejecuta cada 6 horas: `0 */6 * * *`

Para cambiar la frecuencia, editá `k8s/cronjob.yaml`:

```yaml
spec:
  schedule: "0 */6 * * *"  # Cada 6 horas
  # schedule: "0 */12 * * *"  # Cada 12 horas
  # schedule: "0 9,21 * * *"  # A las 9 AM y 9 PM
  # schedule: "0 0 * * *"     # Una vez al día (medianoche)
```

Luego aplicar el cambio:

```bash
kubectl apply -f k8s/cronjob.yaml
```

## Troubleshooting

### Ver datos guardados

```bash
# Crear pod para inspeccionar el PVC
kubectl run -n mercadolibre-monitor -it --rm inspect \
  --image=alpine \
  --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"inspect","image":"alpine","command":["/bin/sh"],"volumeMounts":[{"name":"data","mountPath":"/data"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"mercadolibre-data"}}]}}'

# Dentro del pod:
cat /data/.mercadolibre_monitor.json
```

### Limpiar todo

```bash
kubectl delete namespace mercadolibre-monitor
```

## Ajustes para RKE2

Si usás RKE2, asegurate de:

1. **StorageClass**: Verificar qué storageClass tenés disponible:
   ```bash
   kubectl get storageclass
   ```

   Actualizar `k8s/pvc.yaml` con el nombre correcto:
   ```yaml
   storageClassName: local-path  # o el que tengas
   ```

2. **Image pull**: Si la imagen está en un registry privado, agregá imagePullSecrets al CronJob.

3. **Network policies**: Si tenés network policies estrictas, asegurate de permitir tráfico saliente HTTPS.
