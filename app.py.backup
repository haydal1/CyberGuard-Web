from flask import Flask, request, jsonify
import re
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Simple user management (in production, use a database)
users_db = {}

class UserManager:
    @staticmethod
    def get_user(user_id):
        return users_db.get(user_id, {
            'id': user_id,
            'is_premium': False,
            'checks_today': 0,
            'last_check_date': None,
            'total_checks': 0
        })
    
    @staticmethod
    def save_user(user):
        users_db[user['id']] = user
    
    @staticmethod
    def can_make_free_check(user):
        today = datetime.now().date()
        if user['last_check_date'] != today:
            user['checks_today'] = 0
            user['last_check_date'] = today
        return user['checks_today'] < 5
    
    @staticmethod
    def record_check(user):
        user['checks_today'] += 1
        user['total_checks'] += 1
        user['last_check_date'] = datetime.now().date()
        UserManager.save_user(user)

@app.route('/')
def home():
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CyberGuard NG Premium - Nigerian Fraud Protection</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #0056b3, #003d82);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .premium-badge {
            background: linear-gradient(135deg, #FFD700, #FFA500);
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            margin-left: 10px;
        }
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
        }
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 16px;
            transition: background 0.3s;
        }
        .tab.active {
            background: white;
            border-bottom: 3px solid #007bff;
            font-weight: bold;
        }
        .tab-content {
            display: none;
            padding: 30px;
        }
        .tab-content.active {
            display: block;
        }
        .input-group {
            margin-bottom: 20px;
        }
        input, textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #007bff;
        }
        textarea {
            height: 120px;
            resize: vertical;
        }
        .btn {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s;
            margin: 10px 0;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn-premium {
            background: linear-gradient(135deg, #FFD700, #FFA500);
            color: #000;
            font-weight: bold;
        }
        .btn-danger {
            background: linear-gradient(135deg, #dc3545, #c82333);
        }
        .result {
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
            text-align: center;
            font-weight: bold;
            display: none;
        }
        .safe { background: #d4edda; color: #155724; border: 2px solid #c3e6cb; }
        .scam { background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
        .warning { background: #fff3cd; color: #856404; border: 2px solid #ffeaa7; }
        .premium-feature { 
            background: linear-gradient(135deg, #fff8e1, #ffecb3);
            border: 2px dashed #ffa000;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .pricing-cards {
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }
        .pricing-card {
            flex: 1;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
        }
        .pricing-card:hover {
            transform: translateY(-5px);
            border-color: #007bff;
        }
        .pricing-card.premium {
            border-color: #FFD700;
            background: #fffdf6;
        }
        .price {
            font-size: 2em;
            font-weight: bold;
            color: #28a745;
        }
        .price-premium {
            color: #ffa000;
        }
        .user-stats {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 768px) {
            .pricing-cards { flex-direction: column; }
            .tabs { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ CyberGuard NG <span class="premium-badge">PREMIUM</span></h1>
            <p>Advanced Nigerian Fraud Protection with Premium Features</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('scanner')">Security Scanner</button>
            <button class="tab" onclick="switchTab('premium')">Go Premium</button>
            <button class="tab" onclick="switchTab('account')">My Account</button>
        </div>
        
        <!-- SCANNER TAB -->
        <div id="scanner-content" class="tab-content active">
            <div class="user-stats" id="userStats">
                <strong>Account:</strong> Free | <strong>Checks Today:</strong> <span id="checksCount">0</span>/5
            </div>
            
            <div class="section">
                <div class="section-title">Check USSD Code Safety</div>
                <div class="input-group">
                    <input type="text" id="ussdInput" placeholder="Enter USSD code e.g. *901# or *123*password*#" value="*901#">
                </div>
                <button class="btn" onclick="checkUSSD()">🔍 Check USSD Safety</button>
            </div>
            
            <div class="section">
                <div class="section-title">Scan SMS for Scams</div>
                <div class="input-group">
                    <textarea id="smsInput" placeholder="Paste suspicious SMS message here...">Congratulations! You have won 5,000,000 Naira! Call 08012345678 to claim your prize.</textarea>
                </div>
                <button class="btn btn-danger" onclick="checkSMS()">📱 Scan SMS for Fraud</button>
            </div>
            
            <div class="premium-feature" id="premiumFeature" style="display: none;">
                <h3>🚀 Premium Feature Unlocked!</h3>
                <p id="premiumFeatureText"></p>
            </div>
            
            <div id="result" class="result">Ready to protect you from Nigerian fraud...</div>
        </div>
        
        <!-- PREMIUM TAB -->
        <div id="premium-content" class="tab-content">
            <h2>Upgrade to CyberGuard Premium</h2>
            <p>Get advanced protection and unlimited scans</p>
            
            <div class="pricing-cards">
                <div class="pricing-card">
                    <h3>Free</h3>
                    <div class="price">₦0</div>
                    <ul style="text-align: left; margin: 15px 0;">
                        <li>✓ 5 checks per day</li>
                        <li>✓ Basic scanning</li>
                        <li>✗ Advanced detection</li>
                        <li>✗ Priority support</li>
                    </ul>
                    <button class="btn" disabled>Current Plan</button>
                </div>
                
                <div class="pricing-card premium">
                    <h3>Daily Premium</h3>
                    <div class="price price-premium">₦200</div>
                    <ul style="text-align: left; margin: 15px 0;">
                        <li>✓ Unlimited checks</li>
                        <li>✓ Advanced AI detection</li>
                        <li>✓ Detailed reports</li>
                        <li>✓ Priority support</li>
                    </ul>
                    <button class="btn btn-premium" onclick="showPayment('daily')">Get Daily Premium</button>
                </div>
                
                <div class="pricing-card premium">
                    <h3>Weekly Premium</h3>
                    <div class="price price-premium">₦1,000</div>
                    <ul style="text-align: left; margin: 15px 0;">
                        <li>✓ Everything in Daily</li>
                        <li>✓ 7 days access</li>
                        <li>✓ Save ₦400</li>
                    </ul>
                    <button class="btn btn-premium" onclick="showPayment('weekly')">Get Weekly Premium</button>
                </div>
            </div>
            
            <div id="paymentSection" style="display: none;">
                <h3>Complete Your Payment</h3>
                <p id="paymentInstructions"></p>
                <button class="btn btn-premium" onclick="completePayment()">I have paid - Activate Premium</button>
            </div>
        </div>
        
        <!-- ACCOUNT TAB -->
        <div id="account-content" class="tab-content">
            <h2>My Account</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>Status:</strong> <span id="accountStatus">Free User</span></p>
                <p><strong>Checks Today:</strong> <span id="accountChecks">0</span>/5</p>
                <p><strong>Total Checks:</strong> <span id="totalChecks">0</span></p>
                <button class="btn btn-premium" onclick="switchTab('premium')">Upgrade to Premium</button>
            </div>
        </div>
    </div>

    <script>
        let currentUser = 'user_' + Math.random().toString(36).substr(2, 9);
        let selectedPlan = null;
        let userStats = { checks_today: 0, total_checks: 0, is_premium: false };
        
        // Load user stats on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadUserStats();
        });
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName + '-content').classList.add('active');
            
            if (tabName === 'account') {
                updateAccountInfo();
            }
        }
        
        async function loadUserStats() {
            try {
                const response = await fetch('/api/user-stats?user_id=' + currentUser);
                const data = await response.json();
                userStats = data;
                updateUI();
            } catch (error) {
                console.log('Using default stats');
            }
        }
        
        function updateUI() {
            document.getElementById('checksCount').textContent = userStats.checks_today;
            document.getElementById('accountChecks').textContent = userStats.checks_today;
            document.getElementById('totalChecks').textContent = userStats.total_checks;
            document.getElementById('accountStatus').textContent = userStats.is_premium ? 'Premium User 🏆' : 'Free User';
        }
        
        function updateAccountInfo() {
            document.getElementById('accountChecks').textContent = userStats.checks_today;
            document.getElementById('totalChecks').textContent = userStats.total_checks;
            document.getElementById('accountStatus').textContent = userStats.is_premium ? 'Premium User 🏆' : 'Free User';
        }
        
        async function checkUSSD() {
            const code = document.getElementById('ussdInput').value;
            if (!code) return;
            
            try {
                const response = await fetch('/api/check-ussd', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: code, user_id: currentUser })
                });
                
                const result = await response.json();
                showResult(result);
                loadUserStats(); // Refresh stats
            } catch (error) {
                showResult({
                    message: '❌ Network error. Please try again.',
                    type: 'warning'
                });
            }
        }
        
        async function checkSMS() {
            const sms = document.getElementById('smsInput').value;
            if (!sms) return;
            
            try {
                const response = await fetch('/api/check-sms', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sms: sms, user_id: currentUser })
                });
                
                const result = await response.json();
                showResult(result);
                loadUserStats(); // Refresh stats
            } catch (error) {
                showResult({
                    message: '❌ Network error. Please try again.',
                    type: 'warning'
                });
            }
        }
        
        function showResult(data) {
            const result = document.getElementById('result');
            const premiumFeature = document.getElementById('premiumFeature');
            const premiumFeatureText = document.getElementById('premiumFeatureText');
            
            result.textContent = data.message;
            result.className = 'result ' + data.type;
            result.style.display = 'block';
            
            if (data.premium_features) {
                premiumFeatureText.textContent = data.premium_features;
                premiumFeature.style.display = 'block';
            } else {
                premiumFeature.style.display = 'none';
            }
        }
        
        function showPayment(plan) {
            selectedPlan = plan;
            const plans = {
                'daily': 'Send ₦200 via bank transfer to: GTBank - 0123456789 - CyberGuard NG. WhatsApp proof to activate.',
                'weekly': 'Send ₦1,000 via bank transfer to: GTBank - 0123456789 - CyberGuard NG. WhatsApp proof to activate.'
            };
            
            document.getElementById('paymentInstructions').textContent = plans[plan];
            document.getElementById('paymentSection').style.display = 'block';
        }
        
        async function completePayment() {
            alert('🎉 Thank you! Contact us on WhatsApp with your payment proof to activate premium.');
            document.getElementById('paymentSection').style.display = 'none';
        }
    </script>
</body>
</html>
    '''

@app.route('/api/user-stats', methods=['GET'])
def api_user_stats():
    user_id = request.args.get('user_id', 'default')
    user = UserManager.get_user(user_id)
    return jsonify({
        'is_premium': user['is_premium'],
        'checks_today': user['checks_today'],
        'total_checks': user['total_checks']
    })

@app.route('/api/check-ussd', methods=['POST'])
def api_check_ussd():
    data = request.get_json()
    code = data.get('code', '').strip()
    user_id = data.get('user_id', 'default')
    
    user = UserManager.get_user(user_id)
    
    # Check free limit
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited checks.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # Advanced USSD analysis
    safe_codes = ['*901#', '*894#', '*737#', '*919#', '*822#', '*533#', '*322#', '*326#']
    scam_indicators = ['password', 'pin', 'bvn', 'winner', 'won', 'prize', 'lottery', 'claim']
    
    code_lower = code.lower()
    
    if code in safe_codes:
        message = '✅ SAFE - Verified Nigerian bank USSD code'
        result_type = 'safe'
        premium_features = None
    elif any(indicator in code_lower for indicator in scam_indicators):
        message = '🚨 DANGER - This USSD code contains scam patterns!'
        result_type = 'scam'
        premium_features = 'Upgrade to Premium for detailed scam analysis'
    elif re.match(r'^\*\d{3}#$', code):
        message = '✅ LIKELY SAFE - Standard USSD format'
        result_type = 'safe'
        premium_features = None
    else:
        message = '⚠️ UNKNOWN - Verify with service provider'
        result_type = 'warning'
        premium_features = None
    
    return jsonify({
        'message': message,
        'type': result_type,
        'premium_features': premium_features
    })

@app.route('/api/check-sms', methods=['POST'])
def api_check_sms():
    data = request.get_json()
    sms = data.get('sms', '').strip()
    user_id = data.get('user_id', 'default')
    
    user = UserManager.get_user(user_id)
    
    # Check free limit
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited scans.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # Advanced SMS analysis
    sms_lower = sms.lower()
    score = 0
    reasons = []
    
    patterns = {
        'won|prize|lottery|congratulations': 10,
        'bvn|password|pin|verification': 8,
        'urgent|immediately|now|today': 5,
        'call |text |whatsapp': 4,
        'http|://|www\\.': 6,
        'account|bank|security': 4,
    }
    
    for pattern, points in patterns.items():
        if re.search(pattern, sms_lower, re.IGNORECASE):
            score += points
            reasons.append(pattern)
    
    if re.search(r'08[0-9]{8,}', sms):
        score += 5
        reasons.append('nigerian_phone')
    
    if score >= 15:
        message = '🚨 HIGH-RISK SCAM DETECTED!'
        result_type = 'scam'
    elif score >= 10:
        message = '⚠️ SUSPICIOUS MESSAGE - Be careful!'
        result_type = 'warning'
    else:
        message = '✅ Likely legitimate message'
        result_type = 'safe'
    
    premium_features = f'Score: {score}/30 - Detected patterns'
    
    return jsonify({
        'message': message,
        'type': result_type,
        'premium_features': premium_features
    })

@app.route('/api/upgrade-premium', methods=['POST'])
def api_upgrade_premium():
    data = request.get_json()
    user_id = data.get('user_id')
    
    user = UserManager.get_user(user_id)
    user['is_premium'] = True
    UserManager.save_user(user)
    
    return jsonify({
        'success': True,
        'message': 'Premium activated! You now have unlimited access.'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
else:
    application = app
