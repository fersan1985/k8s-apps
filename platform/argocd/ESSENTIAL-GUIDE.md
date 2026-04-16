# ArgoCD - Guía Esencial (20% que da 80% de valor)

## 🎯 Conceptos Core (Lo que DEBES saber)

### 1. Application CRD
Es el recurso principal. Define QUÉ desplegar y DÓNDE.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: mi-app
  namespace: argocd
spec:
  # ORIGEN: De dónde viene el código
  source:
    repoURL: https://github.com/usuario/repo.git
    targetRevision: HEAD  # branch, tag, o commit
    path: apps/mi-app     # carpeta con manifiestos

  # DESTINO: Dónde se despliega
  destination:
    server: https://kubernetes.default.svc
    namespace: mi-app

  # SYNC: Cómo y cuándo sincronizar
  syncPolicy:
    automated:              # Auto-sync activado
      prune: true          # Elimina recursos borrados del repo
      selfHeal: true       # Auto-corrige cambios manuales
```

### 2. App of Apps Pattern (Tu patrón actual)

**¿Por qué?** En vez de crear 10 Applications manualmente, creas 1 que crea las otras 9.

```
root-app (única que creas manualmente)
├── docker-registry (creada automáticamente)
├── meli-monitor (creada automáticamente)
├── keda (creada automáticamente)
└── platform-appset (creada automáticamente)
```

**Tu workflow:**
1. Modificas `argocd-apps/nueva-app.yaml` en Git
2. Push a GitHub
3. ArgoCD detecta el cambio (cada 3 min por defecto)
4. Crea la nueva Application automáticamente

### 3. Sync Policies - Las 3 que importan

| Policy | ¿Qué hace? | ¿Cuándo usarla? |
|--------|-----------|-----------------|
| `automated: {}` | Auto-sync cada 3min | Apps estables (meli-monitor) |
| `manual` | Solo sincroniza cuando tú lo pides | Apps críticas (DB, storage) |
| `prune: true` | Borra recursos eliminados del repo | Siempre (limpieza automática) |
| `selfHeal: true` | Revierte cambios manuales | Siempre (evita drift) |

**Ejemplo manual sync:**
```yaml
syncPolicy: {}  # Sin 'automated' = manual
```

Para sincronizar:
```bash
# Via CLI
argocd app sync mi-app

# Via UI
Click en SYNC en la app
```

### 4. Health Status - ¿Está funcionando?

ArgoCD checkea el estado de tus recursos:

| Status | Significado | Acción |
|--------|-------------|--------|
| ✅ **Healthy** | Todo OK | Nada |
| 🔄 **Progressing** | Deployando | Esperar |
| ⚠️ **Degraded** | Algo falló | Ver logs |
| ❓ **Unknown** | ArgoCD no sabe | Verificar CRDs |

**Ver detalles:**
```bash
# CLI
argocd app get mi-app

# Ver pods específicos
kubectl get pods -n mi-app
kubectl describe pod <pod-name> -n mi-app
```

---

## 🔧 Operaciones Comunes (Tu día a día)

### Crear una nueva app

**Paso 1:** Crea el manifest en tu repo
```bash
# En tu repo local
cd /path/to/k8s-apps
cat > argocd-apps/nueva-app.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nueva-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/fersan1985/k8s-apps.git
    targetRevision: HEAD
    path: apps/nueva-app
  destination:
    server: https://kubernetes.default.svc
    namespace: nueva-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF

git add argocd-apps/nueva-app.yaml
git commit -m "Add nueva-app"
git push
```

**Paso 2:** Espera 3 minutos o fuerza sync
```bash
argocd app sync root-app
```

**Paso 3:** Verifica
```bash
kubectl get applications -n argocd
argocd app get nueva-app
```

### Ver el estado de todas las apps

```bash
# CLI
argocd app list

# Kubernetes
kubectl get applications -n argocd

# UI
http://192.168.0.34:30080
```

### Rollback a versión anterior

```bash
# Ver historial
argocd app history mi-app

# Rollback a revision anterior
argocd app rollback mi-app <revision-id>
```

### Pausar auto-sync (para maintenance)

```bash
# Deshabilitar auto-sync
argocd app set mi-app --sync-policy none

# Rehabilitar
argocd app set mi-app --sync-policy automated
```

---

## 🐛 Troubleshooting (Problemas comunes)

### App en "OutOfSync"

**Causa:** Cambios manuales en K8s no reflejados en Git

**Solución:**
```bash
# Opción 1: Sync forzado (aplica lo de Git)
argocd app sync mi-app --force

# Opción 2: Ver diferencias
argocd app diff mi-app
```

### App en "Degraded"

**Causa:** Recursos unhealthy (pods crasheando, etc)

**Solución:**
```bash
# Ver detalles
argocd app get mi-app

# Ver logs del pod con problemas
kubectl logs -n <namespace> <pod-name>
kubectl describe pod -n <namespace> <pod-name>
```

### App no aparece en UI

**Causa:** Error en el YAML del Application

**Solución:**
```bash
# Ver eventos
kubectl describe application mi-app -n argocd

# Ver logs del operator
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=50
```

### Sync tarda demasiado

**Causa:** Timeout o recursos pesados

**Solución:**
```yaml
# Aumentar timeout en Application
spec:
  syncPolicy:
    retry:
      limit: 5
      backoff:
        duration: 5s
        maxDuration: 5m
```

---

## 📋 Comandos Esenciales (Tu cheatsheet)

```bash
# Login
argocd login 192.168.0.34:30443 --username admin --insecure

# Listar apps
argocd app list

# Ver estado detallado
argocd app get <app-name>

# Sync manual
argocd app sync <app-name>

# Sync forzado (ignora hooks)
argocd app sync <app-name> --force

# Ver diferencias con Git
argocd app diff <app-name>

# Ver logs
argocd app logs <app-name>

# Rollback
argocd app history <app-name>
argocd app rollback <app-name> <revision>

# Delete app (no borra recursos de K8s)
argocd app delete <app-name>

# Delete app + recursos de K8s
argocd app delete <app-name> --cascade
```

---

## 🎓 Workflow recomendado

### Desarrollo local → Git → ArgoCD

```bash
# 1. Desarrolla localmente
cd apps/mi-app
vim deployment.yaml  # Editas tus manifests

# 2. Prueba localmente (opcional pero recomendado)
kubectl apply -f deployment.yaml --dry-run=client

# 3. Commit y push
git add .
git commit -m "Update mi-app: cambio X"
git push

# 4. ArgoCD auto-detecta (3 min) o fuerza sync
argocd app sync mi-app

# 5. Verifica
kubectl get pods -n mi-app
argocd app get mi-app
```

### Crear nueva app (completo)

```bash
# 1. Crea manifests de la app
mkdir -p apps/nueva-app
cat > apps/nueva-app/deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nueva-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nueva-app
  template:
    metadata:
      labels:
        app: nueva-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
EOF

# 2. Crea ArgoCD Application
cat > argocd-apps/nueva-app.yaml <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nueva-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/fersan1985/k8s-apps.git
    targetRevision: HEAD
    path: apps/nueva-app
  destination:
    server: https://kubernetes.default.svc
    namespace: nueva-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF

# 3. Push
git add apps/nueva-app argocd-apps/nueva-app.yaml
git commit -m "Add nueva-app"
git push

# 4. Sync root-app (para que detecte la nueva app)
argocd app sync root-app

# 5. Espera y verifica
argocd app get nueva-app
kubectl get pods -n nueva-app
```

---

## 🔐 Seguridad básica

### Cambiar password inicial

```bash
# Login con password inicial
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
argocd login 192.168.0.34:30443 --username admin --insecure

# Cambiar password
argocd account update-password

# Borrar secret inicial (buena práctica)
kubectl delete secret argocd-initial-admin-secret -n argocd
```

### Crear usuario read-only

Edita `argocd-cm` ConfigMap:
```bash
kubectl edit configmap argocd-cm -n argocd
```

Agrega:
```yaml
data:
  accounts.viewer: apiKey, login
```

Set password:
```bash
argocd account update-password --account viewer
```

---

## 📚 Referencias rápidas

- **Docs oficiales**: https://argo-cd.readthedocs.io/
- **Patterns**: https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/
- **Best Practices**: https://argo-cd.readthedocs.io/en/stable/user-guide/best_practices/

---

## ✅ Checklist de dominio

Sabes el 20% esencial cuando puedes:

- [ ] Crear una nueva Application desde cero
- [ ] Entender por qué una app está OutOfSync
- [ ] Hacer rollback a una versión anterior
- [ ] Troubleshootear una app Degraded
- [ ] Usar App of Apps para gestionar múltiples apps
- [ ] Decidir cuándo usar auto-sync vs manual
- [ ] Ver logs de una app desde ArgoCD CLI

**Si puedes hacer esto, dominas el 80% del uso diario de ArgoCD.**
