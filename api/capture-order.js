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
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const { orderID } = req.body || {};

    if (!orderID) {
        return res.status(400).json({ error: 'orderID is required' });
    }

    const clientId = process.env.PAYPAL_CLIENT_ID;
    const clientSecret = process.env.PAYPAL_CLIENT_SECRET;

    try {
        const auth = Buffer.from(`${clientId}:${clientSecret}`).toString('base64');
        const tokenRes = await postRequest(
            'https://api-m.paypal.com/v1/oauth2/token',
            {
                'Authorization': `Basic ${auth}`,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            'grant_type=client_credentials'
        );

        const accessToken = tokenRes.data.access_token;

        const captureRes = await postRequest(
            `https://api-m.paypal.com/v2/checkout/orders/${orderID}/capture`,
            {
                'Authorization': `Bearer ${accessToken}`,
                'Content-Type': 'application/json'
            },
            null
        );

        if (captureRes.status === 201 || captureRes.status === 200) {
            const captureData = captureRes.data;
            const isCompleted = captureData.status === 'COMPLETED';
            return res.status(200).json({
                verified: isCompleted,
                orderID,
                status: captureData.status,
                details: captureData
            });
        } else {
            return res.status(400).json({ error: 'Order capture failed', details: captureRes.data });
        }
    } catch (err) {
        return res.status(500).json({ error: err.message });
    }
};
