# Guía de Autorización: Google Drive OAuth 2.0 Personal (Etapa 5.5)

> [!IMPORTANT]
> **Propósito**: Autorizar tu cuenta Google personal (`jarmx72@gmail.com`) para obtener tu `GOOGLE_OAUTH_REFRESH_TOKEN` de forma 100% privada y segura desde la Terminal de tu Mac.
> 
> **Seguridad Garantizada**:
> - **Permiso limitado (`drive.file`)**: La aplicación solo podrá leer/escribir archivos creados por ella misma dentro de tu carpeta privada. **NO tiene acceso a tus correos, ni a tus fotos, ni a otros archivos personales de tu Drive**.
> - **Cero Archivos de Claves**: El script local **NO guarda tu token en el disco duro, ni en logs, ni en GitHub**.
> - **Cero Compartir Secretos**: Nunca debes enviar tu Client Secret ni tu Refresh Token en mensajes de chat.

---

## Instrucciones Paso a Paso (6 Pasos Simples)

### Paso 1: Crear Credencial OAuth en Google Cloud (Tipo "Desktop Application")

1. Abre [Google Cloud Console](https://console.cloud.google.com/) con tu cuenta `jarmx72@gmail.com`.
2. Selecciona tu proyecto **Automaton Quant Audit Storage**.
3. Ve a **APIs y servicios** > **Credenciales**.
4. Haz clic en **+ CREAR CREDANCIALES** > **ID de cliente de OAuth**.
5. En **Tipo de aplicación**, selecciona: **Desktop app** (Aplicación para escritorio).
6. En Nombre: `Automaton Desktop Authorizer`.
7. Haz clic en **CREAR**.
8. Copia temporalmente en tu bloc de notas local:
   - **Client ID** (ejemplo: `123456...apps.googleusercontent.com`)
   - **Client Secret** (ejemplo: `GOCSPX-...`)

---

### Paso 2: Ejecutar el Script de Autorización en tu Mac

Abre la Terminal de tu Mac, ve a la carpeta del proyecto y ejecuta el siguiente comando único (reemplazando los valores con tu Client ID y Client Secret del Paso 1):

```bash
GOOGLE_OAUTH_CLIENT_ID="TU_CLIENT_ID_AQUI" GOOGLE_OAUTH_CLIENT_SECRET="TU_CLIENT_SECRET_AQUI" python3 scripts/google_drive_oauth_authorize.py
```

---

### Paso 3: Iniciar Sesión en el Navegador

1. Se abrirá automáticamente una ventana en tu navegador.
2. Selecciona tu cuenta Google personal: `jarmx72@gmail.com`.
3. Si Google muestra una pantalla de "Google no ha verificado esta app":
   - Haz clic en el enlace **Avanzado** (Advanced).
   - Haz clic en **Ir a Automaton Desktop Authorizer (no seguro)**.
4. Otorga permiso para administrar archivos creados por la app (`drive.file`) y haz clic en **Continuar**.
5. Verás el mensaje: *"¡Autorización completada con éxito!"*. Cierra la pestaña del navegador.

---

### Paso 4: Copiar el Refresh Token desde la Terminal

Regresa a tu Terminal de Mac. Verás un bloque de texto que dice:

```text
GOOGLE_OAUTH_REFRESH_TOKEN:
1//0g... (código largo)
```

Copia ese código largo `1//0g...`.

---

### Paso 5: Configurar las Variables en Vercel Production

1. Entra a tu panel de Vercel > Proyecto `automaton-quant-audit-api` > **Settings** > **Environment Variables**.
2. Configura las siguientes variables en el entorno **Production**:

| Variable | Valor |
| :--- | :--- |
| `DURABLE_STORAGE_PROVIDER` | `GOOGLE_DRIVE_OAUTH` |
| `GOOGLE_DRIVE_FOLDER_ID` | Tu ID de carpeta privada (ej. `1abc...`) |
| `GOOGLE_OAUTH_CLIENT_ID` | Tu Client ID del Paso 1 |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Tu Client Secret del Paso 1 |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Tu Refresh Token copiado en el Paso 4 |

---

### Paso 6: Ejecutar Redeploy en Vercel

1. En Vercel, ve a **Deployments**.
2. Haz clic en los tres puntos `...` a la derecha del deployment más reciente y selecciona **Redeploy**.
3. Una vez completado, vuelve a la sesión de chat para realizar la validación final de lectura.
