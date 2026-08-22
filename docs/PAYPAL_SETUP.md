# PayPal Payment Gateway Setup Guide

**Fecha**: 2026-08-22  
**Módulo Implementado**: [`src/economics/payment_gateway.py`](file:///Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system/src/economics/payment_gateway.py)  
**Log de Pagos**: `logs/portfolio/paypal_payment_log.json`  

---

## 1. Credenciales Requeridas de Jorge

Para conectar la cuenta de PayPal de Jorge y permitir la verificación de pagos reales en vivo ($49.00 USD), agrega las siguientes líneas a tu archivo `.env` local en la raíz del proyecto:

```env
# Configuración de Modo PayPal (SANDBOX para pruebas / LIVE para cobros reales)
PAYPAL_MODE=LIVE

# Credenciales de Aplicación PayPal Developer (https://developer.paypal.com/dashboard/applications/live)
PAYPAL_CLIENT_ID=tu_paypal_client_id_live
PAYPAL_CLIENT_SECRET=tu_paypal_client_secret_live
```

> ⚠️ **Invariante Estricta de Seguridad**: NUNCA escribas tus contraseñas personales ni claves secreta directamente en archivos tracked por Git. El archivo `.env` está en `.gitignore`.

---

## 2. Permisos Mínimos Requeridos en PayPal Developer Dashboard

1. Iniciar sesión en [PayPal Developer Dashboard](https://developer.paypal.com/).
2. Ir a **Apps & Credentials** $\rightarrow$ Seleccionar pestaña **LIVE**.
3. Crear o seleccionar la aplicación para **Automaton Quant Audit**.
4. Permisos mínimos necesarios:
   - `Checkout Orders` (Crear y verificar órdenes de cobro).
   - `Transaction Search` (Buscar transacciones confirmadas de $49.00 USD).

---

## 3. Verificación de Integración Live

Una vez ingresadas las credenciales en `.env`, ejecuta la siguiente prueba de verificación de estado:

```bash
python -c "from src.economics.payment_gateway import PayPalPaymentGateway; gw = PayPalPaymentGateway(); print('LIVE Configured:', gw.is_live_configured())"
```

- Si retorna **`LIVE Configured: True`**, la pasarela está lista para verificar pagos reales de $49.00 USD.
- Si un cliente realiza un pago, se ejecuta el registro formal de ingresos:
  ```bash
  python -c "from src.economics.payment_gateway import PayPalPaymentGateway; gw = PayPalPaymentGateway(); gw.verify_payment('PAYPAL-LIVE-123456')"
  ```
