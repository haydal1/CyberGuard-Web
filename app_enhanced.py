from flask import Flask, request, jsonify, render_template_string
import re
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# =============================================
# YOUR BUSINESS CONFIGURATION - UPDATE THESE!
# =============================================
YOUR_BANK_DETAILS = {
    'bank_name': 'ZenithBank',  # ⚠️ CHANGE TO YOUR BANK
    'account_number': '4249996702',  # ⚠️ CHANGE TO YOUR ACCOUNT
    'account_name': 'Aliyu Egwa Usman',  # ⚠️ CHANGE TO YOUR NAME
}

YOUR_CONTACT = {
    'whatsapp_number': '09031769476',  # ⚠️ CHANGE TO YOUR WHATSAPP
    'business_name': 'aliyuhaydar'
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
            'status': 'pending',  # pending, verified, completed, rejected
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
    # ... (same beautiful HTML interface as before, but with enhanced payment system)
    # The full HTML is too long to include here, but we'll update the payment section
    return "Full HTML interface would be here"

@app.route('/api/user-stats', methods=['GET'])
def api_user_stats():
    user_id = request.args.get('user_id', 'default')
    user = UserManager.get_user(user_id)
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
    
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited checks.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # USSD analysis logic (same as before)
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
    
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited scans.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # SMS analysis logic (same as before)
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
    
    # Generate payment instructions
    plan = PRICING_PLANS[plan_type]
    instructions = f"""
💰 Payment Instructions for {plan['name']}:

Amount: ₦{plan['price']: ,}
Bank: {YOUR_BANK_DETAILS['bank_name']}
Account Number: {YOUR_BANK_DETAILS['account_number']}
Account Name: {YOUR_BANK_DETAILS['account_name']}

📱 After payment, WhatsApp screenshot to: {YOUR_CONTACT['whatsapp_number']}
Include your Payment ID: {payment['id']}

We'll activate your premium within 1 hour of payment verification!
    """
    
    return jsonify({
        'success': True,
        'payment_id': payment['id'],
        'instructions': instructions.strip(),
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

# Admin endpoint to verify payments (you would use this manually)
@app.route('/admin/verify-payment', methods=['POST'])
def admin_verify_payment():
    # In production, add authentication here
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
