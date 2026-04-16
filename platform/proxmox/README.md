# Proxmox Ingress

Acceso a Proxmox VE (192.168.0.22:8006) mediante Ingress con SSL de Let's Encrypt.

## Componentes

- **Service**: ClusterIP con Endpoints externos apuntando a 192.168.0.22:8006
- **Ingress**: SSL Termination con Let's Encrypt + ExternalDNS

## Características

- **SSL válido**: Let's Encrypt para `proxmox.cloudsanchez.com`
- **WebSocket**: Soporte para consola noVNC
- **Backend HTTPS**: Nginx → Proxmox via HTTPS (sin validar certificado auto-firmado)
- **Large uploads**: 10GB max body size para ISOs

## Acceso

```
https://proxmox.cloudsanchez.com
```

## Verificación

```bash
# DNS
dig proxmox.cloudsanchez.com

# Certificado
kubectl get certificate -n default

# Ingress
kubectl get ingress -n default proxmox-ingress

# Service y Endpoints
kubectl get svc,endpoints -n default proxmox-external
```

## Documentación completa

Ver: `/Users/fer/Documents/Journaling/insane3c/Insane3C/2026/docs/Proxmox-Ingress-Setup.md`
