# Monitor de Precios MercadoLibre 🛒💰

Aplicación para monitorear precios de productos en MercadoLibre Argentina con notificaciones automáticas.

## Deployment con Helm

### Pre-requisitos

1. Cluster RKE2 funcionando
2. Helm 3 instalado
3. Docker Registry configurado (ver `../docker-registry/`)

### Quick Start

```bash
cd /Users/fer/Documents/Journaling/insane3c/Insane3C/2026/apps/meli_monitor

# 1. Construir y pushear imagen
docker build -t registry.local:5000/meli-monitor:latest .
docker push registry.local:5000/meli-monitor:latest

# 2. Instalar con Helm
helm install meli-monitor ./helm \
  --namespace mercadolibre-monitor \
  --create-namespace

# 3. Verificar
kubectl get cronjob -n mercadolibre-monitor
```

### Configuración

Crear un archivo `values-custom.yaml`:

```yaml
# Registry
image:
  registry: registry.local:5000
  repository: meli-monitor
  tag: latest

# Schedule (cada 6 horas por defecto)
cronjob:
  schedule: "0 */6 * * *"

# Productos a monitorear
products:
  urls:
    - "https://www.mercadolibre.com.ar/procesador-amd-ryzen-9-9950x3d-16-nucleos-32-hilos-57ghz/up/MLAU3072665106"
    - "https://www.mercadolibre.com.ar/otro-producto/..."

# Notificaciones Slack
notifications:
  slack:
    enabled: true
    webhook: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Notificaciones Discord
# notifications:
#   discord:
#     enabled: true
#     webhook: "https://discord.com/api/webhooks/YOUR/WEBHOOK/URL"

# Storage
persistence:
  storageClass: "local-path"
  size: 1Gi
```

Instalar con configuración custom:

```bash
helm install meli-monitor ./helm \
  -f values-custom.yaml \
  --namespace mercadolibre-monitor \
  --create-namespace
```

### Actualizar configuración

```bash
# Editar values-custom.yaml y luego:
helm upgrade meli-monitor ./helm \
  -f values-custom.yaml \
  --namespace mercadolibre-monitor
```

### Agregar productos

Opción 1: Editar `values-custom.yaml` y hacer upgrade

Opción 2: Editar el ConfigMap directamente:

```bash
kubectl edit configmap -n mercadolibre-monitor meli-monitor-meli-monitor-products
```

### Ejecutar manualmente

```bash
# Crear job manual
kubectl create job -n mercadolibre-monitor \
  --from=cronjob/meli-monitor-meli-monitor \
  manual-check

# Ver logs
kubectl logs -n mercadolibre-monitor job/manual-check -f
```

### Ver datos guardados

```bash
# Crear pod para inspeccionar PVC
kubectl run -n mercadolibre-monitor -it --rm inspect \
  --image=alpine \
  --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"inspect","image":"alpine","command":["/bin/sh"],"volumeMounts":[{"name":"data","mountPath":"/data"}]}],"volumes":[{"name":"data","persistentVolumeClaim":{"claimName":"meli-monitor-meli-monitor-data"}}]}}'

# Dentro del pod:
cat /data/.mercadolibre_monitor.json
```

### Desinstalar

```bash
helm uninstall meli-monitor --namespace mercadolibre-monitor
kubectl delete namespace mercadolibre-monitor
```

## Uso Local (sin Kubernetes)

### Instalación

```bash
python3 -m venv venv
source venv/bin/activate  # o .\venv\Scripts\activate en Windows
pip install -r requirements.txt
```

### Comandos

```bash
# Agregar producto
python mercadolibre_monitor.py add "https://www.mercadolibre.com.ar/..."

# Listar productos
python mercadolibre_monitor.py list

# Verificar precios
python mercadolibre_monitor.py check

# Eliminar producto
python mercadolibre_monitor.py remove 1
```

### Automatización con cron

```bash
crontab -e

# Agregar (ejecutar cada 6 horas):
0 */6 * * * cd /path/to/meli_monitor && ./venv/bin/python mercadolibre_monitor.py check
```

## Notificaciones

### Slack

1. Crear webhook: https://api.slack.com/messaging/webhooks
2. Configurar en `values-custom.yaml` o como variable de entorno:
   ```bash
   export SLACK_WEBHOOK="https://hooks.slack.com/services/..."
   ```

### Discord

1. Server Settings → Integrations → Webhooks → New Webhook
2. Configurar en `values-custom.yaml` o como variable de entorno:
   ```bash
   export DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
   ```

## Estructura del Proyecto

```
meli_monitor/
├── Dockerfile                      # Imagen Docker
├── requirements.txt                # Dependencias Python
├── mercadolibre_monitor.py         # Aplicación principal
├── helm/                          # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── namespace.yaml
│       ├── pvc.yaml
│       ├── configmap.yaml
│       ├── secret.yaml
│       ├── cronjob.yaml
│       └── _helpers.tpl
└── k8s/                           # Manifiestos raw (alternativa a Helm)
    ├── namespace.yaml
    ├── pvc.yaml
    ├── configmap.yaml
    └── cronjob.yaml
```

## Características

✅ Monitoreo automático de precios
✅ Detección de bajadas de precio
✅ Detección de cuotas sin interés
✅ Notificaciones a Slack/Discord
✅ Historial de precios
✅ Deployment con Helm o manifiestos raw
✅ Storage persistente

## Troubleshooting

### Ver logs del CronJob

```bash
# Listar jobs
kubectl get jobs -n mercadolibre-monitor

# Ver logs del último job
kubectl logs -n mercadolibre-monitor \
  $(kubectl get jobs -n mercadolibre-monitor -o jsonpath='{.items[-1].metadata.name}')
```

### El scraping falla

MercadoLibre puede cambiar la estructura HTML. Si falla, revisar los logs y actualizar los selectores CSS en `mercadolibre_monitor.py`.

### Registry no funciona

Ver documentación en `../docker-registry/README.md`.
