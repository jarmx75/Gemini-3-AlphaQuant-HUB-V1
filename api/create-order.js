const https = require('https');

function postRequest(url, headers, body) {
    return new Promise((resolve, reject) => {
        const req = https.request(url, { method: 'POST', headers }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                try {
                    resolve({ status: res.statusCode, data: JSON.parse(data) });
                } catch (e) {
                    resolve({ status: res.statusCode, data });
                }
            });
        });
        req.on('error', reject);
        if (body) req.write(body);
        req.end();
    });
}

module.exports = async (req, res) => {
    // Set CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const clientId = process.env.PAYPAL_CLIENT_ID;
    const clientSecret = process.env.PAYPAL_CLIENT_SECRET;

    if (!clientId || !clientSecret) {
        return res.status(500).json({ error: 'Server PayPal credentials missing' });
    }

    try {
        // 1. Get OAuth Token
        const auth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
        const tokenRes = await postRequest(
            'https://api-m.paypal.com/v1/oauth2/token',
            {
                'Authorization': `Basic ${auth}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            'grant_type=client_credentials'
        );

        if (tokenRes.status !== 200 || !tokenRes.data.access_token) {
            return res.status(500).json({ error: 'OAuth authentication failed', details: tokenRes.data });
        }

        const accessToken = tokenRes.data.access_token;

        const productId = (req.body && req.body.product_id) ? req.body.product_id : 'QUANT_AUDIT';
        const amountVal = (productId === 'QUANT_EXECUTION_REALITY_AUDIT') ? '79.00' : '49.00';
        const descVal = (productId === 'QUANT_EXECUTION_REALITY_AUDIT')
            ? 'Automaton Quant Execution Reality Audit ($79 USD)'
            : 'Automaton Quant Audit Verification ($49 USD)';

        // 2. Create Order
        const orderPayload = JSON.stringify({
            intent: 'CAPTURE',
            purchase_units: [{
                amount: {
                    currency_code: 'USD',
                    value: amountVal
                },
                description: descVal
            }],
            application_context: {
                brand_name: 'Automaton Quant Audit',
                landing_page: 'NO_PREFERENCE',
                user_action: 'PAY_NOW',
                return_url: 'https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/sample.html?status=success',
                cancel_url: 'https://jarmx75.github.io/Gemini-3-AlphaQuant-HUB-V1/?status=cancelled'
            }
        });

        const orderRes = await postRequest(
            'https://api-m.paypal.com/v2/checkout/orders',
            {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            orderPayload
        );

        if (orderRes.status === 201 || orderRes.status === 200) {
            const approveLink = orderRes.data.links.find(l => l.rel === 'approve' || l.rel === 'payer-action');
            return res.status(200).json({
                orderID: orderRes.data.id,
                status: orderRes.data.status,
                approvalUrl: approveLink ? approveLink.href : `https://www.paypal.com/checkoutnow?token=${orderRes.data.id}`
            });
        } else {
            return res.status(500).json({ error: 'Failed to create PayPal order', details: orderRes.data });
        }

    } catch (err) {
        return res.status(500).json({ error: err.message });
    }
};
