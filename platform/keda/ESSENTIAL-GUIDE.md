# KEDA - Guía Esencial (20% que da 80% de valor)

## 🎯 ¿Qué es KEDA y por qué lo necesitas?

**KEDA** = Kubernetes Event-Driven Autoscaling

**En español:** Escala tus pods automáticamente basado en eventos (colas, métricas, tiempo, HTTP requests, etc.)

### Sin KEDA (problema):
```yaml
replicas: 3  # Siempre 3 pods, estén o no ocupados
```
- 💸 Desperdicias recursos de noche (3 pods sin tráfico)
- 📉 Insuficientes recursos en picos (solo 3 pods)

### Con KEDA (solución):
```yaml
minReplicaCount: 0      # 0 pods de noche (ahorro)
maxReplicaCount: 10     # Hasta 10 en picos (performance)
# Escala según la carga REAL
```

---

## 🔧 Conceptos Core (Lo que DEBES saber)

### 1. ScaledObject - El recurso principal

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: mi-app-scaler
  namespace: mi-app
spec:
  scaleTargetRef:
    name: mi-app          # Deployment a escalar
  minReplicaCount: 1      # Mínimo de pods
  maxReplicaCount: 10     # Máximo de pods
  triggers:
    - type: cron          # QUÉ trigger usar
      metadata:
        timezone: America/Argentina/Buenos_Aires
        start: 0 9 * * *  # Escala UP a las 9 AM
        end: 0 18 * * *   # Escala DOWN a las 6 PM
        desiredReplicas: "5"
```

### 2. Los 3 Scalers que cubren el 80% de casos

| Scaler | ¿Cuándo usarlo? | Ejemplo de uso |
|--------|----------------|----------------|
| **Cron** | Horarios predecibles | Escalar en horas de trabajo |
| **Prometheus** | Métricas custom | Escalar por requests/seg, CPU custom |
| **HTTP** | Tráfico HTTP | Escalar por requests pendientes |

---

## 📅 Scaler 1: Cron (El más simple)

**Usa cuando:** Tráfico predecible por horario

### Ejemplo: Scaler para horario laboral

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: meli-monitor-business-hours
  namespace: meli-monitor
spec:
  scaleTargetRef:
    name: meli-monitor
  minReplicaCount: 1      # Mínimo 1 pod siempre
  maxReplicaCount: 5      # Máximo 5 pods
  triggers:
    # Horario laboral: 9 AM - 6 PM
    - type: cron
      metadata:
        timezone: America/Argentina/Buenos_Aires
        start: 0 9 * * 1-5     # Lun-Vie 9 AM
        end: 0 18 * * 1-5      # Lun-Vie 6 PM
        desiredReplicas: "3"   # 3 pods en horario laboral

    # Fines de semana: menos carga
    - type: cron
      metadata:
        timezone: America/Argentina/Buenos_Aires
        start: 0 10 * * 0,6    # Sáb-Dom 10 AM
        end: 0 16 * * 0,6      # Sáb-Dom 4 PM
        desiredReplicas: "1"   # 1 pod en finde
```

**Resultado:**
- Lun-Vie 9-18hs: **3 pods**
- Sáb-Dom 10-16hs: **1 pod**
- Resto del tiempo: **1 pod** (minReplicaCount)

### Sintaxis de Cron (recordatorio)

```
┌───────────── minuto (0 - 59)
│ ┌───────────── hora (0 - 23)
│ │ ┌───────────── día del mes (1 - 31)
│ │ │ ┌───────────── mes (1 - 12)
│ │ │ │ ┌───────────── día de la semana (0 - 6) (0 = Domingo)
│ │ │ │ │
* * * * *

Ejemplos:
0 9 * * *      = Todos los días a las 9 AM
0 9 * * 1-5    = Lunes a Viernes a las 9 AM
0 0 * * 0      = Domingos a medianoche
*/15 * * * *   = Cada 15 minutos
```

---

## 📊 Scaler 2: Prometheus (Métricas custom)

**Usa cuando:** Escalas por métricas de tu app (requests/seg, queue depth, etc.)

### Prerequisito: Exponer métricas de Prometheus

Tu app debe exponer métricas en `/metrics`:

```python
# Python Flask ejemplo
from prometheus_client import Counter, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

requests_total = Counter('http_requests_total', 'Total HTTP requests')

app = Flask(__name__)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

@app.route('/')
def hello():
    requests_total.inc()
    return "Hello!"
```

### Ejemplo: Escalar por requests/segundo

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: meli-monitor-http-scaler
  namespace: meli-monitor
spec:
  scaleTargetRef:
    name: meli-monitor
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: http_requests_per_second
        query: |
          rate(http_requests_total{app="meli-monitor"}[1m])
        threshold: "10"   # Escala si >10 req/seg por pod
```

**Cómo funciona:**
1. KEDA consulta Prometheus cada 30 seg
2. Si `requests/seg > 10` → Agrega un pod
3. Si `requests/seg < 10` → Elimina un pod

### Ejemplo: Escalar por cola de mensajes

```yaml
triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.monitoring.svc:9090
      query: |
        sum(rabbitmq_queue_messages{queue="work_queue"})
      threshold: "30"  # Escala si hay >30 mensajes pendientes
```

---

## 🌐 Scaler 3: HTTP (Tráfico web)

**Usa cuando:** Escalas por requests HTTP pendientes

### Ejemplo: Escalar por requests concurrentes

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: docker-registry-http-scaler
  namespace: docker-registry
spec:
  scaleTargetRef:
    name: docker-registry
  minReplicaCount: 0      # Puede bajar a 0 (scale-to-zero)
  maxReplicaCount: 5
  triggers:
    - type: http
      metadata:
        host: registry.home.local
        targetPendingRequests: "100"  # Escala si hay >100 req pendientes
```

**¿Cuándo escala a 0?**
- Cuando no hay tráfico HTTP por 5 minutos (configurable)
- **Ventaja:** Ahorro máximo de recursos
- **Desventaja:** Cold start (primer request tarda ~5 seg)

---

## 🔄 Combinando múltiples triggers

Puedes usar VARIOS triggers al mismo tiempo. KEDA escala según el que pida MÁS replicas.

### Ejemplo: Cron + Prometheus

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: meli-monitor-combined
  namespace: meli-monitor
spec:
  scaleTargetRef:
    name: meli-monitor
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    # Trigger 1: Horario laboral (baseline)
    - type: cron
      metadata:
        timezone: America/Argentina/Buenos_Aires
        start: 0 9 * * 1-5
        end: 0 18 * * 1-5
        desiredReplicas: "3"

    # Trigger 2: Escalar por carga real
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: rate(http_requests_total{app="meli-monitor"}[1m])
        threshold: "20"
```

**Cómo funciona:**
- 9-18hs: **Mínimo 3 pods** (por cron)
- Si requests/seg > 20: **Escala hasta 10** (por prometheus)
- Fuera de horario: **1 pod** (minReplicaCount)

---

## 🐛 Troubleshooting (Problemas comunes)

### 1. ScaledObject creado pero no escala

**Diagnóstico:**
```bash
# Ver estado del ScaledObject
kubectl describe scaledobject <name> -n <namespace>

# Ver logs de KEDA operator
kubectl logs -n keda -l app=keda-operator --tail=50

# Ver si KEDA ve el trigger
kubectl get hpa -n <namespace>
```

**Causa común:** Trigger mal configurado (query de Prometheus inválida, timezone mal, etc.)

### 2. Escala muy lento

**Causa:** Configuración conservadora por defecto

**Solución:** Ajustar `cooldownPeriod` y `pollingInterval`

```yaml
spec:
  cooldownPeriod: 60     # Espera 60 seg antes de scale down
  pollingInterval: 15    # Checkea trigger cada 15 seg
  triggers:
    # ...
```

### 3. No escala a 0

**Causa 1:** `minReplicaCount: 1`
**Solución:** Cambia a `minReplicaCount: 0`

**Causa 2:** No todos los scalers soportan scale-to-zero (Cron NO lo soporta)
**Solución:** Usa HTTP o Prometheus scaler

---

## 📋 Comandos Esenciales

```bash
# Listar ScaledObjects
kubectl get scaledobjects -A

# Ver detalles de un ScaledObject
kubectl describe scaledobject <name> -n <namespace>

# Ver el HPA creado por KEDA
kubectl get hpa -n <namespace>

# Ver eventos de scaling
kubectl get events -n <namespace> --sort-by='.lastTimestamp'

# Ver logs de KEDA operator
kubectl logs -n keda -l app=keda-operator --tail=100 -f

# Ver métricas actuales (si tienes metrics-server)
kubectl top pods -n <namespace>

# Delete ScaledObject (vuelve a replicas originales)
kubectl delete scaledobject <name> -n <namespace>
```

---

## 🎓 Workflow recomendado

### 1. Deployar tu app normal (sin KEDA)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mi-app
spec:
  replicas: 2  # Valor inicial
  # ...
```

### 2. Observar el comportamiento real

```bash
# Ver métricas de uso
kubectl top pods -n mi-app

# Ver tráfico (si tienes Prometheus)
# Identifica patrones: ¿Picos? ¿Horarios? ¿Qué métrica predice la carga?
```

### 3. Crear ScaledObject

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: mi-app-scaler
  namespace: mi-app
spec:
  scaleTargetRef:
    name: mi-app
  minReplicaCount: 1
  maxReplicaCount: 5
  triggers:
    - type: cron  # Empezar con el más simple
      metadata:
        timezone: America/Argentina/Buenos_Aires
        start: 0 9 * * *
        end: 0 18 * * *
        desiredReplicas: "3"
```

### 4. Aplicar y observar

```bash
kubectl apply -f scaledobject.yaml
kubectl get scaledobject mi-app-scaler -n mi-app -w
kubectl get hpa -n mi-app -w
```

### 5. Iterar

- Ajusta thresholds basado en observaciones
- Agrega más triggers si es necesario
- Combina cron + prometheus para mejor control

---

## 🎯 Casos de uso reales para tu homelab

### Caso 1: Meli Monitor (scraping periódico)

**Problema:** Scraping cada hora, pero app corre 24/7 desperdiciando recursos.

**Solución:**
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: meli-monitor-scaler
  namespace: meli-monitor
spec:
  scaleTargetRef:
    name: meli-monitor
  minReplicaCount: 0    # 0 pods cuando no scracea
  maxReplicaCount: 1    # Solo necesita 1 pod
  triggers:
    - type: cron
      metadata:
        timezone: America/Argentina/Buenos_Aires
        start: 0 * * * *     # Arranca al inicio de cada hora
        end: 10 * * * *      # Apaga a los 10 min
        desiredReplicas: "1"
```

**Ahorro:** ~83% de recursos (10 min/hora en vez de 60 min/hora)

### Caso 2: Docker Registry (bajo tráfico)

**Problema:** Registry corre 24/7 pero solo se usa al deployar.

**Solución:** Scale-to-zero con HTTP scaler
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: docker-registry-scaler
  namespace: docker-registry
spec:
  scaleTargetRef:
    name: docker-registry
  minReplicaCount: 0
  maxReplicaCount: 2
  triggers:
    - type: http
      metadata:
        host: registry.home.local
        targetPendingRequests: "5"
```

**Ahorro:** Casi 100% cuando no hay deploys

### Caso 3: Web app con picos predecibles

**Problema:** Tráfico alto 9-18hs, bajo de noche.

**Solución:** Cron + Prometheus
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: webapp-scaler
  namespace: webapp
spec:
  scaleTargetRef:
    name: webapp
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: cron
      metadata:
        start: 0 9 * * 1-5
        end: 0 18 * * 1-5
        desiredReplicas: "3"
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        query: rate(http_requests_total[1m])
        threshold: "50"
```

---

## ✅ Checklist de dominio

Dominas el 20% esencial cuando puedes:

- [ ] Crear un ScaledObject con Cron trigger
- [ ] Entender cuándo usar minReplicaCount: 0 vs 1
- [ ] Diagnosticar por qué un ScaledObject no escala
- [ ] Combinar 2 triggers (Cron + Prometheus)
- [ ] Ver las métricas que KEDA usa para escalar
- [ ] Calcular el ahorro de recursos vs deployment estático

**Si puedes hacer esto, dominas el 80% del uso diario de KEDA.**

---

## 📚 Scalers disponibles (referencia rápida)

| Scaler | Usa cuando | Ejemplo |
|--------|-----------|---------|
| `cron` | Horarios predecibles | Horario laboral |
| `prometheus` | Métricas custom | Requests/seg, CPU, memoria custom |
| `http` | Tráfico HTTP | APIs, web apps |
| `cpu` | CPU del pod | Apps CPU-intensive |
| `memory` | Memoria del pod | Apps memory-intensive |
| `rabbitmq` | Cola RabbitMQ | Workers de cola |
| `redis` | Redis list/stream | Cache, queues |
| `postgresql` | Filas en DB | Procesamiento de DB |

**Tip:** El 90% de casos se cubren con **cron**, **prometheus** y **http**.

---

## 📚 Referencias

- **Docs oficiales**: https://keda.sh/docs/
- **Scalers**: https://keda.sh/docs/scalers/
- **Ejemplos**: https://github.com/kedacore/sample-go-rabbitmq
