# Pi-hole Ingress

Acceso a Pi-hole (192.168.0.3:80) mediante Ingress con SSL de Let's Encrypt.

## Componentes

- **Service**: ClusterIP con Endpoints externos apuntando a 192.168.0.3:80
- **Ingress**: SSL Termination con Let's Encrypt + ExternalDNS

## Características

- **SSL válido**: Let's Encrypt para `pihole.cloudsanchez.com`
- **Backend HTTP**: Nginx → Pi-hole via HTTP (puerto 80)
- **Path `/admin`**: Acceso a la UI de administración

## Acceso

```
https://pihole.cloudsanchez.com/admin
```

## Verificación

```bash
# DNS
dig pihole.cloudsanchez.com

# Certificado
kubectl get certificate -n default pihole-cloudsanchez-tls

# Ingress
kubectl get ingress -n default pihole-ingress

# Service y Endpoints
kubectl get svc,endpoints -n default pihole-external
```

## Notas Importantes

### Solo Web UI

Este Ingress expone **únicamente la interfaz web** de Pi-hole.

El servicio DNS (puerto 53) sigue funcionando normalmente en 192.168.0.3 para toda la red local, independiente de este Ingress.

### Path Behavior

Pi-hole redirige automáticamente:
- `/admin` → `/admin/login` (si no autenticado)
- `/admin/login` → Página de login
- `/admin/index.php` → Dashboard

El `PathType: Prefix` captura todas estas rutas.

### Backend Protocol

Pi-hole sirve HTTP en puerto 80 (no HTTPS). Nginx hace SSL termination.

## Troubleshooting

### Redirect Loops

Si experimentas loops de redirección, configura Pi-hole para confiar en el proxy:

```bash
ssh root@192.168.0.3
sudo nano /etc/pihole/pihole.toml

# Agregar:
[webserver]
  trust_proxy = true

pihole restartdns
```

### 502 Bad Gateway

Verifica conectividad desde cluster:
```bash
kubectl run test-curl --image=curlimages/curl:latest --rm -it --restart=Never -- curl -I http://192.168.0.3/admin/
```

## Documentación completa

Ver: `/Users/fer/Documents/Journaling/insane3c/Insane3C/2026/docs/Pi-hole-Ingress-Setup.md`
