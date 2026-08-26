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

const fs = require('fs');
const path = require('path');

module.exports = async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    const { txn_id, orderID, email } = req.body || {};
    const targetTxn = txn_id || orderID;

    const logFile = path.join(__dirname, '..', 'logs', 'portfolio', 'paypal_payment_log.json');
    let verifiedRecord = null;

    if (fs.existsSync(logFile)) {
        try {
            const raw = fs.readFileSync(logFile, 'utf8');
            const payments = JSON.parse(raw);
            if (Array.isArray(payments)) {
                verifiedRecord = payments.find(p => p.verified && (
                    (targetTxn && p.txn_id === targetTxn) ||
                    (email && p.payer_email === email)
                ));
            }
        } catch (e) {}
    }

    if (verifiedRecord) {
        return res.status(200).json({
            verified: true,
            status: 'COMPLETED',
            payment_record: verifiedRecord,
            architecture: 'PAYPAL_HOSTED_LINKS_WEBHOOK_IPN'
        });
    }

    return res.status(200).json({
        verified: false,
        status: 'AWAITING_INDEPENDENT_PAYPAL_VERIFICATION',
        message: 'Audit completion requires asynchronous PayPal Webhook/IPN verification for Hosted Payment Link transaction.'
    });
};
