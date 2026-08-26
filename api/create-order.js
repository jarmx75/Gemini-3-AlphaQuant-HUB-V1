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

    const hostedLinks = {
        'QUANT_AUDIT_49': process.env.PAYPAL_LINK_49 || 'https://www.paypal.com/ncp/payment/SH9CKB2WSX728',
        'QUANT_EXECUTION_REALITY_AUDIT_79': process.env.PAYPAL_LINK_79 || 'https://www.paypal.com/ncp/payment/TMMGL3YRC8PFN',
        'COMPLETE_QUANT_VALIDATION_BUNDLE_96': process.env.PAYPAL_LINK_96 || 'https://www.paypal.com/ncp/payment/2Y3RX97HNWXY6'
    };

    const productId = (req.body && req.body.product_id) ? req.body.product_id : 'QUANT_AUDIT_49';
    const paymentLink = hostedLinks[productId] || hostedLinks['QUANT_AUDIT_49'];

    return res.status(200).json({
        status: 'DEPRECATED_MIGRATED_TO_HOSTED_LINKS',
        product_id: productId,
        approvalUrl: paymentLink,
        message: 'PayPal Orders API has been migrated to PayPal Hosted Payment Links. Use direct hosted link.'
    });
};
