# Guía Paso a Paso: Cómo Dar Acceso a GitHub para Publicar la Landing Page

**Fecha**: 2026-08-22  
**Objetivo**: Permitir que Automaton publique automáticamente la Landing Page en **GitHub Pages** (gratuito con HTTPS) sin necesidad de pagar hosting.  
**Tu Rol**: Generar un token de acceso seguro en GitHub y pegarlo en `config/.env`. **No necesitas saber programar.**

---

## 📌 Pasos Simples (5 Minutos)

### PASO 1: Entrar a la Sección de Tokens en GitHub
Abre en tu navegador la siguiente dirección:  
👉 **[https://github.com/settings/tokens/new](https://github.com/settings/tokens/new)**  
*(Si te pide iniciar sesión, ingresa a tu cuenta personal de GitHub).*

---

### PASO 2: Configurar el Token
1. **Note (Nombre)**: Escribe `Automaton Deployment`.
2. **Expiration (Expiración)**: Selecciona `90 days` o `No expiration`.
3. **Select Scopes (Permisos)**: Marca las siguientes casillas de verificación:
   - [x] **`repo`** (Full control of private repositories)
   - [x] **`workflow`** (Update GitHub Action workflows)

---

### PASO 3: Generar y Copiar el Token
1. Ve al final de la página y haz clic en el botón verde **Generate token**.
2. Verás en pantalla un texto que comienza con **`ghp_...`** (ejemplo: `ghp_1234567890abcdef...`).
3. Haz clic en el ícono de copiar.

---

### PASO 4: Pegar el Token en tu archivo `config/.env`
Abre el archivo `config/.env` en tu editor o bloc de notas y agrega esta línea:

```env
GITHUB_TOKEN=pega_aqui_tu_token_ghp
```

---

## 🛑 Lo Que NO Debes Dar NUNCA
- ❌ **NO des tu contraseña personal de GitHub**.
- ❌ **NO des tu contraseña de correo**.
- ❌ **NO des ningún dato bancario o de tarjeta**.

---

## 🔍 ¿Qué Hará Automaton Una Vez Que Agregues el Token?
1. Automaton creará el repositorio remoto seguro `trading-autonomous-system`.
2. Subirá la carpeta `docs/public_landing/`.
3. Activará **GitHub Pages con HTTPS** automáticamente.
4. Tu sitio web quedará público en `https://jorgeatilano.github.io/trading-autonomous-system/` listo para recibir clientes.
