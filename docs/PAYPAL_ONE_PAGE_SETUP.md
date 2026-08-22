# Guía Simple de 1 Página: Configuración de PayPal para Jorge

**Fecha**: 2026-08-22  
**Objetivo**: Permitir que Automaton reciba pagos reales de $49.00 USD mediante PayPal.  
**Tu Rol**: Simplemente copiar 2 textos desde tu panel de PayPal a tu archivo de configuración `config/.env`. **No necesitas saber programar.**

---

## 📌 Los 6 Pasos Simples

### PASO 1: Entrar al Panel de Desarrolladores de PayPal
Abre en tu navegador la siguiente dirección:  
👉 **[https://developer.paypal.com/dashboard/applications/live](https://developer.paypal.com/dashboard/applications/live)**

---

### PASO 2: Ir a "Apps & Credentials"
1. Inicia sesión con tu cuenta personal o de negocios de PayPal.
2. En el menú superior o lateral, haz clic en **Apps & Credentials**.
3. Asegúrate de seleccionar la pestaña **LIVE** (en la esquina superior derecha).

---

### PASO 3: Crear una REST API App
1. Haz clic en el botón azul **Create App**.
2. Escribe el nombre de la app: `Automaton Quant Audit`.
3. Haz clic en **Create App**.

---

### PASO 4: Copiar los 2 Códigos
Verás en pantalla dos textos principales:
1. **Client ID** (se ve como una cadena larga de letras y números).
2. **Secret** (haz clic en *Show* para copiarlo).

---

### PASO 5: Requisito de Cuenta de PayPal
> ℹ️ **Nota Importante**: Para recibir cobros reales en modo **LIVE**, PayPal requiere que tu cuenta sea de tipo **Business** o **Premier** y esté verificada. Si tu cuenta actual es personal, PayPal te dará la opción gratuita de cambiarla a Business desde la misma plataforma.

---

### PASO 6: Pegar los 2 Códigos en tu archivo `config/.env`
Abre el archivo `config/.env` en tu computadora (o en tu editor de texto) y pega los valores en estas dos líneas:

```env
PAYPAL_MODE=LIVE
PAYPAL_CLIENT_ID=pega_aqui_tu_client_id
PAYPAL_CLIENT_SECRET=pega_aqui_tu_client_secret
```

---

## 🔍 ¿Cómo Saber si Quedó Bien Configurado?

Abre una terminal y ejecuta este único comando:

```bash
python -m src.economics.payment_gateway --doctor
```

Si todo está correcto, la respuesta mostrará:
```text
PAYPAL_CONFIGURED=true
PAYPAL_MODE=LIVE
AUTHENTICATION=PASS
CHECKOUT=PASS
```

*(El sistema nunca imprimirá ni revelará tus contraseñas o claves secretas en la pantalla).*
