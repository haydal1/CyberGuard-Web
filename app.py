from flask import Flask, request, jsonify
import re
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# =============================================
# YOUR ACTUAL BUSINESS CONFIGURATION
# =============================================
YOUR_BANK_DETAILS = {
    'bank_name': 'ZenithBank',
    'account_number': '4249996702',
    'account_name': 'Aliyu Egwa Usman',
}

YOUR_CONTACT = {
    'whatsapp_number': '09031769476',
    'business_name': 'CyberGuard NG',
    'email': 'aliyuhaydal9@gmail.com'
}

PRICING_PLANS = {
    'daily': {'price': 200, 'duration': 1, 'name': 'Daily Premium'},
    'weekly': {'price': 1000, 'duration': 7, 'name': 'Weekly Premium'},
    'monthly': {'price': 3000, 'duration': 30, 'name': 'Monthly Premium'}
}
# =============================================

# Storage (in production, use a database)
users_db = {}
payments_db = {}

class UserManager:
    @staticmethod
    def get_user(user_id):
        return users_db.get(user_id, {
            'id': user_id,
            'is_premium': False,
            'premium_until': None,
            'premium_plan': None,
            'checks_today': 0,
            'last_check_date': None,
            'total_checks': 0,
            'payment_pending': False
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
        return user['checks_today'] < 5 or user['is_premium']
    
    @staticmethod
    def record_check(user):
        user['checks_today'] += 1
        user['total_checks'] += 1
        user['last_check_date'] = datetime.now().date()
        UserManager.save_user(user)
    
    @staticmethod
    def activate_premium(user, plan_type, duration_days):
        user['is_premium'] = True
        user['premium_plan'] = plan_type
        user['premium_until'] = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d')
        user['payment_pending'] = False
        UserManager.save_user(user)

class PaymentManager:
    @staticmethod
    def create_payment(user_id, plan_type, phone_number):
        payment_id = f"pay_{datetime.now().strftime('%Y%m%d%H%M%S')}_{user_id}"
        payment = {
            'id': payment_id,
            'user_id': user_id,
            'plan_type': plan_type,
            'phone_number': phone_number,
            'amount': PRICING_PLANS[plan_type]['price'],
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'verified_at': None,
            'bank_details': YOUR_BANK_DETAILS
        }
        payments_db[payment_id] = payment
        return payment
    
    @staticmethod
    def get_payment(payment_id):
        return payments_db.get(payment_id)
    
    @staticmethod
    def update_payment_status(payment_id, status):
        payment = payments_db.get(payment_id)
        if payment:
            payment['status'] = status
            payment['verified_at'] = datetime.now().isoformat() if status == 'verified' else None
            return True
        return False

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
        .payment-instructions {
            background: #e7f3ff;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
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
                <strong>Account:</strong> <span id="accountType">Free</span> | 
                <strong>Checks Today:</strong> <span id="checksCount">0</span>/<span id="maxChecks">5</span>
                <span id="premiumInfo" style="display: none;">| <strong>Premium Until:</strong> <span id="premiumUntil"></span></span>
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
                    <button class="btn btn-premium" onclick="showPaymentForm('daily')">Get Daily Premium</button>
                </div>
                
                <div class="pricing-card premium">
                    <h3>Weekly Premium</h3>
                    <div class="price price-premium">₦1,000</div>
                    <ul style="text-align: left; margin: 15px 0;">
                        <li>✓ Everything in Daily</li>
                        <li>✓ 7 days access</li>
                        <li>✓ Save ₦400</li>
                    </ul>
                    <button class="btn btn-premium" onclick="showPaymentForm('weekly')">Get Weekly Premium</button>
                </div>
            </div>
            
            <div id="paymentSection" style="display: none;">
                <div class="payment-instructions">
                    <h3>Complete Your Payment</h3>
                    <div class="input-group">
                        <input type="text" id="phoneNumber" placeholder="Enter your WhatsApp number" required>
                    </div>
                    <div id="paymentDetails"></div>
                    <button class="btn btn-premium" onclick="initiatePayment()">Get Payment Instructions</button>
                </div>
                
                <div id="paymentInstructions" style="display: none; margin-top: 20px;">
                    <h4>💰 Payment Instructions:</h4>
                    <div id="instructionsContent"></div>
                    <p><strong>📱 WhatsApp Proof to: <span id="whatsappNumber">09031769476</span></strong></p>
                    <div class="input-group">
                        <input type="text" id="paymentIdInput" placeholder="Your Payment ID will appear here" readonly>
                    </div>
                    <button class="btn" onclick="checkPaymentStatus()">Check Payment Status</button>
                </div>
            </div>
        </div>
        
        <!-- ACCOUNT TAB -->
        <div id="account-content" class="tab-content">
            <h2>My Account</h2>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>User ID:</strong> <span id="accountUserId"></span></p>
                <p><strong>Status:</strong> <span id="accountStatus">Free User</span></p>
                <p><strong>Checks Today:</strong> <span id="accountChecks">0</span>/<span id="accountMaxChecks">5</span></p>
                <p><strong>Total Checks:</strong> <span id="totalChecks">0</span></p>
                <p id="accountPremiumInfo" style="display: none;"><strong>Premium Plan:</strong> <span id="premiumPlan"></span></p>
                <p id="accountPremiumUntil" style="display: none;"><strong>Premium Until:</strong> <span id="premiumUntilDate"></span></p>
                <button class="btn btn-premium" onclick="switchTab('premium')">Upgrade to Premium</button>
            </div>
        </div>
    </div>

    <script>
        let currentUser = 'user_' + Math.random().toString(36).substr(2, 9);
        let selectedPlan = null;
        let currentPaymentId = null;
        
        document.addEventListener('DOMContentLoaded', function() {
            loadUserStats();
            document.getElementById('accountUserId').textContent = currentUser;
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
                updateUI(data);
            } catch (error) {
                console.log('Using default stats');
            }
        }
        
        function updateUI(stats) {
            const isPremium = stats.is_premium;
            const maxChecks = isPremium ? '∞' : '5';
            
            document.getElementById('checksCount').textContent = stats.checks_today;
            document.getElementById('maxChecks').textContent = maxChecks;
            document.getElementById('accountType').textContent = isPremium ? 'Premium 🏆' : 'Free';
            document.getElementById('accountChecks').textContent = stats.checks_today;
            document.getElementById('accountMaxChecks').textContent = maxChecks;
            document.getElementById('totalChecks').textContent = stats.total_checks;
            document.getElementById('accountStatus').textContent = isPremium ? 'Premium User 🏆' : 'Free User';
            
            if (isPremium && stats.premium_until) {
                document.getElementById('premiumInfo').style.display = 'inline';
                document.getElementById('premiumUntil').textContent = stats.premium_until;
                document.getElementById('accountPremiumInfo').style.display = 'block';
                document.getElementById('accountPremiumUntil').style.display = 'block';
                document.getElementById('premiumPlan').textContent = stats.premium_plan || 'Premium';
                document.getElementById('premiumUntilDate').textContent = stats.premium_until;
            } else {
                document.getElementById('premiumInfo').style.display = 'none';
                document.getElementById('accountPremiumInfo').style.display = 'none';
                document.getElementById('accountPremiumUntil').style.display = 'none';
            }
        }
        
        function updateAccountInfo() {
            loadUserStats();
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
                loadUserStats();
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
                loadUserStats();
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
            
            if (data.limit_reached) {
                setTimeout(() => switchTab('premium'), 2000);
            }
        }
        
        function showPaymentForm(plan) {
            selectedPlan = plan;
            document.getElementById('paymentSection').style.display = 'block';
            document.getElementById('paymentInstructions').style.display = 'none';
            
            const plans = {
                'daily': { price: 200, name: 'Daily Premium' },
                'weekly': { price: 1000, name: 'Weekly Premium' }
            };
            
            const planInfo = plans[plan];
            document.getElementById('paymentDetails').innerHTML = `
                <p><strong>Plan:</strong> ${planInfo.name}</p>
                <p><strong>Amount:</strong> ₦${planInfo.price}</p>
                <p><strong>Duration:</strong> ${plan === 'daily' ? '24 hours' : '7 days'}</p>
            `;
        }
        
        async function initiatePayment() {
            const phone = document.getElementById('phoneNumber').value;
            if (!phone) {
                alert('Please enter your WhatsApp number');
                return;
            }
            
            try {
                const response = await fetch('/api/initiate-payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        user_id: currentUser, 
                        plan_type: selectedPlan,
                        phone_number: phone 
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    currentPaymentId = result.payment_id;
                    document.getElementById('instructionsContent').innerHTML = result.instructions.replace(/\n/g, '<br>');
                    document.getElementById('paymentIdInput').value = result.payment_id;
                    document.getElementById('paymentInstructions').style.display = 'block';
                    document.getElementById('whatsappNumber').textContent = result.whatsapp_number;
                    
                    alert('Payment instructions generated! Please follow them carefully.');
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }
        
        async function checkPaymentStatus() {
            if (!currentPaymentId) {
                alert('No payment ID found. Please initiate a payment first.');
                return;
            }
            
            try {
                const response = await fetch(`/api/check-payment-status?payment_id=${currentPaymentId}&user_id=${currentUser}`);
                const result = await response.json();
                
                if (result.success) {
                    if (result.payment_status === 'verified' || result.user_premium) {
                        alert('🎉 Payment verified! Your premium account is now active!');
                        loadUserStats();
                        switchTab('scanner');
                    } else {
                        alert('Payment status: ' + result.payment_status + '. We are still verifying your payment.');
                    }
                } else {
                    alert('Error checking payment: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }
    </script>
</body>
</html>
    '''

@app.route('/api/user-stats', methods=['GET'])
def api_user_stats():
    user_id = request.args.get('user_id', 'default')
    user = UserManager.get_user(user_id)
    
    # Check if premium has expired
    if user['premium_until'] and datetime.now().strftime('%Y-%m-%d') > user['premium_until']:
        user['is_premium'] = False
        user['premium_plan'] = None
        user['premium_until'] = None
        UserManager.save_user(user)
    
    return jsonify({
        'is_premium': user['is_premium'],
        'premium_until': user['premium_until'],
        'premium_plan': user['premium_plan'],
        'checks_today': user['checks_today'],
        'total_checks': user['total_checks'],
        'payment_pending': user['payment_pending']
    })

@app.route('/api/check-ussd', methods=['POST'])
def api_check_ussd():
    data = request.get_json()
    code = data.get('code', '').strip()
    user_id = data.get('user_id', 'default')
    
    user = UserManager.get_user(user_id)
    
    # Check premium status and limits
    if user['premium_until'] and datetime.now().strftime('%Y-%m-%d') > user['premium_until']:
        user['is_premium'] = False
        user['premium_plan'] = None
        user['premium_until'] = None
    
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited checks.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # USSD analysis logic
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
        premium_features = '🔍 Premium Analysis: Contains known scam keywords' if user['is_premium'] else 'Upgrade to Premium for detailed scam analysis'
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
    
    # Check premium status and limits
    if user['premium_until'] and datetime.now().strftime('%Y-%m-%d') > user['premium_until']:
        user['is_premium'] = False
        user['premium_plan'] = None
        user['premium_until'] = None
    
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited scans.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # SMS analysis logic
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
    
    premium_features = f'🔍 Premium Analysis: Score {score}/30 - {", ".join(reasons[:2])}' if user['is_premium'] else 'Upgrade to Premium for detailed threat analysis'
    
    return jsonify({
        'message': message,
        'type': result_type,
        'premium_features': premium_features
    })

@app.route('/api/initiate-payment', methods=['POST'])
def api_initiate_payment():
    data = request.get_json()
    user_id = data.get('user_id')
    plan_type = data.get('plan_type')
    phone_number = data.get('phone_number')
    
    if not user_id or not plan_type or not phone_number:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    if plan_type not in PRICING_PLANS:
        return jsonify({'success': False, 'message': 'Invalid plan type'})
    
    # Create payment record
    payment = PaymentManager.create_payment(user_id, plan_type, phone_number)
    
    # Update user to show payment pending
    user = UserManager.get_user(user_id)
    user['payment_pending'] = True
    UserManager.save_user(user)
    
    # Generate payment instructions with YOUR details
    plan = PRICING_PLANS[plan_type]
    instructions = f"""Amount: ₦{plan['price']: ,}
Bank: {YOUR_BANK_DETAILS['bank_name']}
Account Number: {YOUR_BANK_DETAILS['account_number']}
Account Name: {YOUR_BANK_DETAILS['account_name']}

After payment, WhatsApp screenshot to: {YOUR_CONTACT['whatsapp_number']}
Include your Payment ID: {payment['id']}

We'll activate your premium within 1 hour of payment verification!"""
    
    return jsonify({
        'success': True,
        'payment_id': payment['id'],
        'instructions': instructions,
        'whatsapp_number': YOUR_CONTACT['whatsapp_number']
    })

@app.route('/api/check-payment-status', methods=['GET'])
def api_check_payment_status():
    payment_id = request.args.get('payment_id')
    user_id = request.args.get('user_id')
    
    payment = PaymentManager.get_payment(payment_id)
    if not payment or payment['user_id'] != user_id:
        return jsonify({'success': False, 'message': 'Payment not found'})
    
    user = UserManager.get_user(user_id)
    
    return jsonify({
        'success': True,
        'payment_status': payment['status'],
        'user_premium': user['is_premium'],
        'premium_until': user['premium_until']
    })

# Admin endpoint to verify payments
@app.route('/admin/verify-payment', methods=['POST'])
def admin_verify_payment():
    # Simple authentication (in production, use proper auth)
    auth = request.headers.get('Authorization')
    if auth != 'Bearer CyberGuardAdmin2024':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    data = request.get_json()
    payment_id = data.get('payment_id')
    action = data.get('action')  # 'approve' or 'reject'
    
    payment = PaymentManager.get_payment(payment_id)
    if not payment:
        return jsonify({'success': False, 'message': 'Payment not found'})
    
    if action == 'approve':
        PaymentManager.update_payment_status(payment_id, 'verified')
        # Activate premium for user
        user = UserManager.get_user(payment['user_id'])
        plan = PRICING_PLANS[payment['plan_type']]
        UserManager.activate_premium(user, payment['plan_type'], plan['duration'])
        
        return jsonify({
            'success': True, 
            'message': f'Premium activated for user {payment["user_id"]}'
        })
    elif action == 'reject':
        PaymentManager.update_payment_status(payment_id, 'rejected')
        user = UserManager.get_user(payment['user_id'])
        user['payment_pending'] = False
        UserManager.save_user(user)
        return jsonify({'success': True, 'message': 'Payment rejected'})
    else:
        return jsonify({'success': False, 'message': 'Invalid action'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
else:
    application = app
