# Guía de Configuración: Google Drive OAuth 2.0 Personal para Almacenamiento Durable

> [!IMPORTANT]
> **Propósito**: Migrar la autenticación de Google Drive de "Cuenta de Servicio" a "OAuth 2.0 Personal".
> 
> **¿Por qué este cambio?**: Una cuenta de servicio de Google Cloud es un usuario virtual secundario con 0 bytes de almacenamiento. Al intentar subir archivos a una carpeta compartida de tu Google Drive personal (`jarmx72@gmail.com`), Google Drive rechaza la escritura porque el archivo consumiría la cuota del creador (la cuenta de servicio), la cual no tiene almacenamiento asignado.
> 
> Al usar OAuth 2.0 con tu cuenta personal (`jarmx72@gmail.com`), los archivos guardados pertenecen directamente a tu cuenta y utilizan tus 15 GB de almacenamiento gratuito.

---

## Principios de Seguridad
1. **Tu Drive sigue siendo 100% privado**: Los archivos se guardarán exclusivamente dentro de tu carpeta privada de Google Drive.
2. **No se expone tu contraseña**: Se utiliza un `Refresh Token` seguro que solo autoriza el acceso a la carpeta configurada.
3. **Cero Secretos en Chat o GitHub**: Nunca compartas tu Client Secret ni tu Refresh Token en mensajes de chat, repositorios ni logs públicos.
4. **Estado Comercial**: El sistema continuará en preparación parcial (`PARTIAL`) hasta completar la validación posterior. No actives cobros reales todavía.

---

## Paso 1: Crear Credenciales OAuth 2.0 en Google Cloud Console

1. Abre [Google Cloud Console](https://console.cloud.google.com/) con tu cuenta `jarmx72@gmail.com`.
2. Asegúrate de tener seleccionado el proyecto **Automaton Quant Audit Storage** (o el proyecto que creaste anteriormente).
3. En el menú de navegación izquierdo, ve a **APIs & Services** > **Credentials** (APIs y servicios > Credenciales).
4. Haz clic en el botón superior **+ CREATE CREDENTIALS** y selecciona **OAuth client ID**.
5. Si se te solicita configurar la Pantalla de consentimiento (OAuth Consent Screen):
   - Tipo de usuario: **External** (o Internal si está disponible).
   - Nombre de la app: `Automaton Storage`.
   - Correo de soporte y desarrollador: `jarmx72@gmail.com`.
   - Haz clic en **Save and Continue** (Guardar y continuar) hasta finalizar.
6. En **Application type** (Tipo de aplicación), selecciona **Web application**.
7. En Nombre: `Automaton Drive OAuth Client`.
8. En **Authorized redirect URIs** (URIs de redireccionamiento autorizadas), haz clic en **+ ADD URI** e ingresa:
   ```text
   https://developers.google.com/oauthplayground
   ```
9. Haz clic en **CREATE**.
10. Aparecerá una ventana con:
    - **Client ID** (identificador de cliente)
    - **Client Secret** (secreto de cliente)
    *Copia ambos valores temporalmente en un block de notas privado local.*

---

## Paso 2: Obtener tu Refresh Token usando Google OAuth Playground

1. Abre en tu navegador la herramienta oficial: [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
2. En la esquina superior derecha, haz clic en el ícono de engranaje ⚙️ (**OAuth 2.0 configuration**).
3. Marca la casilla **Use your own OAuth credentials** (Usar sus propias credenciales OAuth).
4. Pega tu **OAuth Client ID** y **OAuth Client Secret** creados en el Paso 1.
5. En el panel izquierdo (**Step 1: Select & authorize APIs**), busca la sección **Drive API v3**.
6. Selecciona el scope:
   `https://www.googleapis.com/auth/drive`
7. Haz clic en el botón azul **Authorize APIs**.
8. Inicia sesión con tu cuenta Google personal (`jarmx72@gmail.com`). Si aparece una advertencia de "Google no ha verificado esta app", haz clic en **Avanzado** (Advanced) y luego en **Ir a Automaton Storage (no seguro)**.
9. Concede permisos para administrar archivos de Google Drive y haz clic en **Continuar**.
10. Serás redirigido de vuelta al OAuth Playground en el **Step 2: Exchange authorization code for tokens**.
11. Haz clic en el botón azul **Exchange authorization code for tokens**.
12. En la parte inferior derecha verás el campo:
    **Refresh token**
    *Copia este valor con cuidado. Es la clave permanente que permitirá a Vercel escribir en tu Drive de forma duradera.*

---

## Paso 3: Configurar las Variables en Vercel Production

1. Entra a tu panel de Vercel > Proyecto `automaton-quant-audit-api` > **Settings** > **Environment Variables**.
2. Agrega o actualiza las siguientes 5 variables en el entorno **Production**:

| Nombre de Variable | Valor a Configurar |
| :--- | :--- |
| `DURABLE_STORAGE_PROVIDER` | `GOOGLE_DRIVE_OAUTH` |
| `GOOGLE_DRIVE_FOLDER_ID` | Tu ID de carpeta privada (ej. `1abc...`) |
| `GOOGLE_OAUTH_CLIENT_ID` | Tu Client ID del Paso 1 |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Tu Client Secret del Paso 1 |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | Tu Refresh Token del Paso 2 |

3. En Vercel, ve a la pestaña **Deployments**, haz clic en los tres puntos `...` del último deployment y selecciona **Redeploy**.

---

## Próximos Pasos

> [!CAUTION]
> - No elimines la Cuenta de Servicio todavía. Se mantendrá como respaldo de compatibilidad.
> - No actives ventas reales ni hagas pruebas POST adicionales hasta que completemos la verificación de salud (`/api/storage-health`).
> - Si tienes alguna duda en algún paso, vuelve a la sesión de chat y pregúntame antes de continuar.
