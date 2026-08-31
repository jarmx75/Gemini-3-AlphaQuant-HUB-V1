# Plan de Validación Controlada en Producción (Sprint #36.13 / Etapa 5.1)

## 1. Estado Actual de Evidencia

| Capa de Prueba | Estado Comprobado | Clasificación de Evidencia | Razón |
|---|---|---|---|
| **Lectura de Google Drive** | **VALIDADO (200 OK)** | `PRODUCTION_READ_ONLY_VALIDATED` | El endpoint `/api/storage-health` en Vercel Production devolvió `health: "HEALTHY"` al leer metadatos de la carpeta privada. |
| **Escritura Controlada en Google Drive** | **NO VALIDADA** | `LOCAL_FAKE_CREDENTIAL_TEST` | Las pruebas de escritura previas se ejecutaron localmente con credenciales falsas/de ejemplo. No hay confirmación de objetos creados en la carpeta real de Google Drive. |
| **Preparación Comercial** | **PARTIAL** | `PARTIAL` | El fulfillment comercial real permanece bloqueado de forma segura hasta confirmar la escritura real en producción. |

---

## 2. Jerarquía Estricta de Clasificación de Evidencia

1. **`MOCK_TEST`**: Pruebas unitarias en memoria con mocks. Cero red, cero Drive real.
2. **`LOCAL_FAKE_CREDENTIAL_TEST`**: Ejecución local CLI con variables de ejemplo o credenciales simuladas. **Nunca puede declarar persistencia real en Google Drive ni `COMMERCIAL_FULFILLMENT_READINESS = READY_FOR_LIMITED_PILOT`.**
3. **`LOCAL_REAL_CREDENTIAL_TEST`**: Ejecución local con credenciales reales (deshabilitada por defecto para no exponer secretos locales).
4. **`PRODUCTION_READ_ONLY_VALIDATED`**: Petición GET real al endpoint `/api/storage-health` desplegado en Vercel confirmando la lectura de metadatos de la carpeta.
5. **`PRODUCTION_CONTROLLED_WRITE_VALIDATED`**: Prueba controlada invocada mediante un endpoint dedicado en producción que crea como máximo 3 objetos de prueba marcados `TEST_ONLY` bajo `internal-tests/` y confirma sus IDs de retorno.
6. **`NOT_VALIDATED`**: Estado no verificado por defecto.

---

## 3. ¿Por qué el Estado Comercial es `PARTIAL`?

- El sistema ha verificado en producción que la API de Vercel puede autenticar con Google Drive y leer el nombre y metadatos de tu carpeta privada.
- Sin embargo, para evitar falsa confianza, el sistema **no asume** que los permisos de escritura funcionen hasta que se ejecute una prueba explícita desde Vercel Production hacia la carpeta privada.
- Mientras esa prueba no se realice, la plataforma mantiene el estado `COMMERCIAL_FULFILLMENT_READINESS = PARTIAL` y responde `503 Service Unavailable` a cualquier intento de subida de cliente sin pago verificado.

---

## 4. Diseño del Futuro Endpoint de Validación (`/api/internal-storage-validation`)

Para validar la escritura en producción sin poner en riesgo la seguridad ni crear clientes o cobros falsos, se ha preparado un endpoint especializado y bloqueado por defecto:

### Reglas de Seguridad:
1. **Método**: Acepta **únicamente POST**. Peticiones GET son rechazadas con `405 Method Not Allowed`.
2. **Autenticación requerida**: Debe recibir el token secreto `INTERNAL_STORAGE_VALIDATION_TOKEN` en los encabezados HTTP o en el body JSON. Peticiones sin token o con token incorrecto son rechazadas con `401 Unauthorized` / `403 Forbidden`.
3. **Confirmación explícita**: Exige `"confirm_internal_test": true` en el body JSON.
4. **Aislamiento absoluto**:
   - Crea como máximo **3 objetos de prueba** marcados `TEST_ONLY` bajo el prefijo `internal-tests/`:
     1. Archivo CSV inocuo de prueba (`internal-tests/INTERNAL_TEST_*.csv`).
     2. Reporte de auditoría de prueba (`internal-tests/INTERNAL_TEST_*.json`).
     3. Certificado de prueba (`internal-tests/INTERNAL_TEST_*.json`).
   - Hereda la privacidad de la carpeta privada (`public_sharing = DISABLED_PRIVATE_FOLDER_ONLY`).
   - Cero llamadas a PayPal, cero cobros reales, cero envío de correos electrónicos.
   - Cero impacto en métricas comerciales ($0.00 ingresos, 0 clientes).
5. **No expone secretos**: Devuelve referencias sanitizadas o truncadas (`gfile_...`), sin llaves JSON ni Folder IDs reales.

---

## 5. Instrucciones para la Futura Ejecución (Etapa Posterior)

Cuando decidas autorizar la prueba real de escritura en producción:
1. Se configurará temporalmente una clave secreta en la variable de entorno `INTERNAL_STORAGE_VALIDATION_TOKEN` de Vercel Production.
2. Se enviará una sola petición POST autorizada.
3. El sistema verificará los IDs de retorno de los 3 objetos creados en tu Google Drive bajo la carpeta `internal-tests/`.
4. Una vez confirmados los IDs, la evidencia pasará a `PRODUCTION_CONTROLLED_WRITE_VALIDATED`.
