# GUÍA DE CONFIGURACIÓN DE GOOGLE DRIVE COMO ALMACENAMIENTO DURABLE

---

## 1. ⚠️ Advertencia Inicial Importante

- **Cuenta recomendada**: Utiliza una **cuenta Google personal** dedicada a tu negocio (que incluye 15 GB de almacenamiento gratuito). **No uses una cuenta escolar u organizacional administrada**, ya que suelen tener restricciones de permisos de API externa.
- **Privacidad**: Tu carpeta debe mantenerse 100% **privada**. Nunca compartas la carpeta con el público ni generes enlaces públicos de acceso.
- **Seguridad de Secretos**: El archivo de clave secreta (JSON) de la cuenta de servicio es confidencial. **Nunca lo subas a GitHub, ni lo compartas en chats ni en repositorios públicos.**

---

## 2. Paso 1: Crear la Carpeta Privada en Google Drive

1. Ingresa a tu [Google Drive](https://drive.google.com) personal.
2. Crea una nueva carpeta con el nombre recomendado: `Automaton Quant Audit - Private Client Files`.
3. Abre la carpeta recién creada y observa la barra de direcciones de tu navegador. La URL se verá así:
   `https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j_EXAMPLE_ID`
4. Copia únicamente el texto al final de la URL (después de `/folders/`). Este es tu **`GOOGLE_DRIVE_FOLDER_ID`** (ejemplo: `1a2b3c4d5e6f7g8h9i0j_EXAMPLE_ID`).

---

## 3. Paso 2: Crear el Proyecto y Cuenta de Servicio en Google Cloud Console

> 💡 **Nota**: Este procedimiento es **100% gratuito** y **no requiere tarjeta de crédito**.

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Haz clic en el menú desplegable superior de proyectos y selecciona **"Nuevo Proyecto"**.
3. Nombra tu proyecto (ejemplo: `Automaton-Quant-Storage`) y haz clic en **Crear**.
4. En la barra de búsqueda superior, busca **"Google Drive API"** y haz clic en **Habilitar**.
5. En el menú lateral izquierdo, ve a **APIs y servicios -> Credenciales**.
6. Haz clic en **"Crear credenciales"** en la parte superior y selecciona **"Cuenta de servicio" (Service Account)**.
7. Asigna un nombre (ejemplo: `automaton-storage-sa`) y haz clic en **Crear y continuar**. No es necesario asignar roles del proyecto; haz clic en **Listo**.
8. En la lista de Cuentas de Servicio, haz clic sobre la cuenta recién creada.
9. Ve a la pestaña **Claves (Keys)** -> **Agregar clave** -> **Crear clave nueva**.
10. Selecciona el formato **JSON** y haz clic en **Crear**. Se descargará automáticamente un archivo `.json` a tu computadora.
11. Copia la dirección de correo de la cuenta de servicio (se ve así: `automaton-storage-sa@automaton-quant-storage.iam.gserviceaccount.com`).

---

## 4. Paso 3: Compartir la Carpeta Privada con la Cuenta de Servicio

1. Regresa a tu carpeta en [Google Drive](https://drive.google.com).
2. Haz clic derecho sobre la carpeta `Automaton Quant Audit - Private Client Files` -> **Compartir**.
3. En el campo de personas, pega la dirección de correo de la cuenta de servicio (`automaton-storage-sa@...`).
4. Asegúrate de que el rol asignado sea **Editor**.
5. Desmarca la casilla "Notificar a las personas" y haz clic en **Compartir**.

> 🔒 *La carpeta ahora está vinculada de forma segura exclusivamente con tu robot de almacenamiento sin ser visible para nadie más.*

---

## 5. Paso 4: Configurar las Variables de Entorno en Vercel

Ingresa a tu proyecto en [Vercel](https://vercel.com) -> **Settings** -> **Environment Variables** y agrega las siguientes 3 variables:

| Nombre de Variable | Valor a Ingresar |
|---|---|
| `DURABLE_STORAGE_PROVIDER` | `GOOGLE_DRIVE` |
| `GOOGLE_DRIVE_FOLDER_ID` | Tu `FOLDER_ID` copiado en el Paso 1 (ej. `1a2b3c4d5e6f...`) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Todo el contenido de texto del archivo `.json` descargado en el Paso 2 |

> 📌 **Cómo copiar el JSON**: Abre el archivo `.json` descargado con un editor de texto (Notepad, TextEdit o VS Code), selecciona **todo el texto** (desde `{` hasta `}`), cópialo y pégalo directamente en el valor de la variable en Vercel.

---

## 6. Paso 5: Redesplegar en Vercel y Leer los Estados

Después de guardar las 3 variables, realiza un **Redeploy** de tu proyecto en Vercel.

Para verificar el estado, ejecuta el monitor de lectura:
```bash
python3 src/economics/manual_revenue_funnel_monitor.py
```

### Significado de los Estados:

| Estado | Significado | Diagnóstico / Acción |
|---|---|---|
| `HEALTHY` | La cuenta de servicio tiene acceso de lectura/escritura a tu carpeta privada. | Conexión lista. |
| `NOT_CONFIGURED` | Faltan variables en Vercel o contienen texto plantilla. | Revisa las variables en Vercel. |
| `PERMISSION_DENIED` | La carpeta no fue compartida con el correo de la cuenta de servicio. | Repite el Paso 3 (compartir con rol Editor). |
| `FOLDER_NOT_FOUND` | El `GOOGLE_DRIVE_FOLDER_ID` es incorrecto o la carpeta está en la papelera. | Revisa el ID de la URL de la carpeta. |
| `STORAGE_ERROR` / `FAIL_CLOSED` | El JSON pegado en Vercel está incompleto o mal formado. | Revisa que el JSON empiece con `{` y termine con `}`. |

---

## 7. Resultado de la Validación de Producción

Para consultar el estado técnico en producción sin comprometer la seguridad ni exponer datos sensibles, realiza una consulta GET al endpoint de salud:

`GET https://automaton-quant-audit-api.vercel.app/api/storage-health`

### Interpretación de Resultados:

- **`HEALTHY`**: Google Drive está conectado correctamente en modo técnico. Las ventas y cobros aún **no se activan**; el estado comercial se mantiene en `PARTIAL` a la espera de una prueba de flujo controlada.
- **`PERMISSION_DENIED`**: La cuenta de servicio no puede acceder a la carpeta. Revisa que compartiste la carpeta con el correo de la cuenta de servicio (`client_email`) otorgando rol de **Editor**.
- **`FOLDER_NOT_FOUND`**: El `GOOGLE_DRIVE_FOLDER_ID` es incorrecto o la carpeta está en la papelera de Google Drive.
- **`NOT_CONFIGURED`**: Revisa que las 3 variables de entorno (`DURABLE_STORAGE_PROVIDER`, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`) estén guardadas en Vercel Production.
- **`STORAGE_ERROR`**: Revisa que el despliegue en Vercel se haya completado tras configurar las variables.

---

## 8. 🔴 ADVERTENCIA FINAL DE OPERACIÓN

> **No actives ventas ni compartas enlaces comerciales hasta que Antigravity confirme HEALTHY y se realice una validación controlada posterior.**

