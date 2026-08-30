# GUÍA DE CONFIGURACIÓN DE ALMACENAMIENTO DURABLE

---

## 1. ¿Por qué es obligatorio el Almacenamiento Durable?

En plataformas serverless como **Vercel**, el sistema de archivos local (`/tmp`) es **efímero**. Esto significa que cualquier archivo subido por un cliente (estrategias en CSV o JSON), así como sus reportes de auditoría y certificados generados, se **eliminan automáticamente** cuando la función serverless finaliza o se reinicia.

Para poder operar comercialmente con clientes reales, es **estrictamente obligatorio** contar con un almacenamiento en la nube permanente (durable) compatible con la API S3. 

Si el almacenamiento durable **no está configurado**, el sistema opera en modo **FAIL-CLOSED (Bloqueo Seguro)**:
- Rechaza cargas de archivos comerciales con error `503 Service Unavailable`.
- No ejecuta auditorías comerciales pagadas sin garantía de persistencia.
- No emite certificados finales ni envía correos de entrega.
- Reporta `COMMERCIAL_FULFILLMENT_READINESS = NOT_READY`.

---

## 2. Proveedor Recomendado: Cloudflare R2 (o AWS S3 / S3-Compatible)

Se recomienda **Cloudflare R2** como opción inicial por las siguientes razones:
- **Compatibilidad total con API S3**: Funciona directamente con la abstracción S3 del sistema.
- **Cero costos de transferencia de salida (Egress Free)**: No cobra por las descargas de reportes o certificados.
- **Capa gratuita permanente alta**: Permite iniciar sin costos fijos iniciales.

*Nota: El sistema también es 100% compatible con AWS S3, Backblaze B2, DigitalOcean Spaces o MinIO.*

---

## 3. Datos exactos que el propietario debe obtener del proveedor

Al crear una cuenta y un bucket en Cloudflare R2 (o AWS S3), debes obtener únicamente estos 5 datos:

1. **Nombre del Bucket** (ejemplo: `quant-audit-customer-files`)
2. **Access Key ID** (clave de acceso API)
3. **Secret Access Key** (clave secreta API)
4. **Endpoint URL** (dirección de la API S3 de tu bucket, ej. `https://<account_id>.r2.cloudflarestorage.com`)
5. **Región** (ej. `auto` para R2, o `us-east-1` para AWS S3)

> ⚠️ **IMPORTANTE DE SEGURIDAD**: Guarda tus claves secretas en un gestor de contraseñas seguro. **Nunca** compartas ni publiques la clave secreta en código, chats ni repositorios.

---

## 4. Variables de Entorno a Configurar en Vercel

Ingresa al panel de tu proyecto en **Vercel -> Settings -> Environment Variables** y agrega las siguientes variables de entorno para los entornos de `Production` y `Preview`:

| Nombre de Variable | Ejemplo de Valor | Descripción |
|---|---|---|
| `DURABLE_STORAGE_PROVIDER` | `CLOUDFLARE_R2` | Identificador del proveedor (`CLOUDFLARE_R2`, `AWS_S3`, `S3_COMPATIBLE`) |
| `DURABLE_STORAGE_BUCKET` | `quant-audit-customer-files` | Nombre exacto del bucket creado |
| `DURABLE_STORAGE_ENDPOINT` | `https://<account_id>.r2.cloudflarestorage.com` | URL del endpoint S3 proporcionado por tu proveedor |
| `DURABLE_STORAGE_REGION` | `auto` | Región del bucket |
| `DURABLE_STORAGE_ACCESS_KEY_ID` | `tu_access_key_id_aqui` | Clave de acceso pública S3 |
| `DURABLE_STORAGE_SECRET_ACCESS_KEY` | `tu_secret_access_key_aqui` | Clave de acceso secreta S3 |
| `DURABLE_STORAGE_PUBLIC_BASE_URL` | `https://cdn.tu-dominio.com` | (Opcional) URL pública o CDN si usas un dominio propio |

---

## 5. Cómo verificar que quedó configurado correctamente

Una vez agregadas las variables en Vercel y desplegado el proyecto, ejecuta localmente o mediante la API el monitor de estado:

```bash
python3 src/economics/manual_revenue_funnel_monitor.py
```

En el reporte JSON de salida (`logs/portfolio/manual_revenue_funnel_snapshot.json`), verifica el bloque `durable_storage`:

```json
{
  "durable_storage": {
    "durable_storage_provider": "CLOUDFLARE_R2",
    "durable_storage_configured": true,
    "durable_storage_health": "HEALTHY",
    "commercial_fulfillment_status": "FULFILLMENT_READY"
  },
  "COMMERCIAL_FULFILLMENT_READINESS": "READY"
}
```

---

## 6. Significado de los Estados del Sistema

| Estado | Significado | Acción del Sistema |
|---|---|---|
| `NOT_CONFIGURED` | Las variables de entorno S3 no han sido configuradas o son valores plantilla. | Bloqueo seguro activado (`FAIL_CLOSED`). Cargas comerciales rechazadas. |
| `HEALTHY` | Conexión S3 verificada con éxito y bucket accesible para escritura. | Sistema comercial activo (`FULFILLMENT_READY`). |
| `CONFIGURED_LITE` | Variables configuradas correctamente en entorno ligero sin SDK completo. | Preparado para conexión serverless. |
| `FAIL_CLOSED` | El chequeo de salud falló o falta configuración. | Bloqueo de seguridad total. Ningún archivo es aceptado. |
| `STORAGE_ERROR` / `STORAGE_UNHEALTHY` | Credenciales incorrectas, bucket inexistente o error de red. | Bloqueo automático de fulfillment comercial. |

---

## 7. ⚠️ ADVERTENCIA EXPLICITA DE OPERACIÓN

> 🔴 **ADVERTENCIA CRÍTICA**:
> **No habilites ventas reales, no promociones la plataforma ni inicies contacto comercial con prospectos hasta que el estado verificado en el monitor sea estrictamente `HEALTHY` y `COMMERCIAL_FULFILLMENT_READINESS = READY`.**
