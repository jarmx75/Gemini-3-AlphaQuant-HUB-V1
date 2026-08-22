# Public Landing Deployment & Hosting Guide

**Fecha**: 2026-08-22  
**Estado del Paquete**: 🟢 **READY FOR DEPLOYMENT**  
**Directorio del Paquete**: [`docs/public_landing/`](file:///Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system/docs/public_landing/)  
- Landing principal: `docs/public_landing/index.html`
- Certificado de muestra: `docs/public_landing/sample.html`

---

## 1. Verificación de Seguridad y Contenido del Paquete

- [x] **Cero enlaces locales `file://`**: Todos los enlaces utilizan rutas relativas públicas (`sample.html`, `#pricing`, `#audit-form`).
- [x] **Cero afirmaciones engañosas**: Banner visible de **`MODELLED / NOT GUARANTEED`** en el héroe y disclaimer obligatorio en el pie de página.
- [x] **Banner de Muestra**: `sample.html` incluye el banner prominente **`SAMPLE / DEMONSTRATION ONLY`**.
- [x] **Precio Confirmado**: Exactamente **$49.00 USD** por auditoría individual.

---

## 2. Opciones de Despliegue Público Recomendas

### Opción A: Vercel (Recomendado — 1 minuto)
1. Instalar Vercel CLI o conectar repositorio GitHub a Vercel.
2. Ejecutar desde el directorio del proyecto:
   ```bash
   npx vercel docs/public_landing --prod
   ```
3. O bien ingresar el token de acceso de Vercel en `.env`: `VERCEL_TOKEN=your_token_here`.

### Opción B: Netlify CLI
1. Ejecutar:
   ```bash
   npx netlify deploy --dir=docs/public_landing --prod
   ```
2. O ingresar el token de acceso en `.env`: `NETLIFY_AUTH_TOKEN=your_token_here`.

### Opción C: GitHub Pages
1. Crear un repositorio público en GitHub o habilitar GitHub Pages en la rama `main` apuntando a la carpeta `/docs/public_landing`.
2. URL pública resultante: `https://<tu_usuario>.github.io/<repositorio>/`.

---

## 3. Credencial Requerida de Jorge
Para que Antigravity o el pipeline automatizado publique la Landing Page a producción automáticamente, se requiere una de las siguientes tres credenciales en `.env`:

```env
# Opción 1: Vercel Access Token
VERCEL_TOKEN=...

# Opción 2: Netlify Personal Access Token
NETLIFY_AUTH_TOKEN=...

# Opción 3: GitHub Personal Access Token (para GitHub Pages)
GITHUB_TOKEN=...
```
