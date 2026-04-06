# Monitor de Precios MercadoLibre 🛒💰

Aplicación CLI para monitorear precios de productos en MercadoLibre Argentina y recibir notificaciones cuando bajan de precio o tienen cuotas sin interés.

## Instalación

```bash
# Instalar dependencias
pip install requests beautifulsoup4

# Hacer ejecutable (opcional)
chmod +x mercadolibre_monitor.py
```

## Uso

### Agregar un producto para monitorear

```bash
python mercadolibre_monitor.py add "https://www.mercadolibre.com.ar/producto/..."
```

### Ver productos monitoreados

```bash
python mercadolibre_monitor.py list
```

### Verificar precios

```bash
python mercadolibre_monitor.py check
```

Este comando:
- Revisa todos los productos guardados
- Compara con el precio anterior
- Muestra notificaciones si hay bajadas de precio
- Detecta si ahora hay cuotas sin interés

### Eliminar un producto

```bash
python mercadolibre_monitor.py remove 1
```

## Automatización con cron

Para verificar precios automáticamente cada 6 horas:

```bash
# Editar crontab
crontab -e

# Agregar esta línea (ajustar la ruta)
0 */6 * * * cd /ruta/a/tu/directorio && python3 mercadolibre_monitor.py check > /tmp/meli_check.log 2>&1
```

Para recibir notificaciones por email cuando hay cambios:

```bash
0 */6 * * * cd /ruta/a/tu/directorio && python3 mercadolibre_monitor.py check | mail -s "MercadoLibre Monitor" tu@email.com
```

## Características

✅ Monitoreo de precios en tiempo real
✅ Historial de precios guardado
✅ Detección automática de bajadas de precio
✅ Detección de cuotas sin interés
✅ Almacenamiento local en JSON
✅ Sin necesidad de API key o autenticación

## Almacenamiento

Los datos se guardan en `~/.mercadolibre_monitor.json`

## Ejemplo de uso

```bash
# Agregar productos
python mercadolibre_monitor.py add "https://www.mercadolibre.com.ar/notebook-..."
python mercadolibre_monitor.py add "https://www.mercadolibre.com.ar/auriculares-..."

# Ver lista
python mercadolibre_monitor.py list

# Verificar precios (ejecutar periódicamente)
python mercadolibre_monitor.py check
```

## Notas

- El scraping puede fallar si MercadoLibre cambia la estructura de su sitio
- Se recomienda no hacer verificaciones muy frecuentes (cada 6-12 horas está bien)
- Las notificaciones se muestran en la terminal al ejecutar `check`
