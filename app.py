from flask import Flask, request, jsonify
import re
from datetime import datetime, timedelta
import os
import json
import smtplib
import random
import hashlib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    'business_name': 'CyberGuard NG'
}

PRICING_PLANS = {
    'daily': {'price': 200, 'duration': 1, 'name': 'Daily Premium'},
    'weekly': {'price': 1000, 'duration': 7, 'name': 'Weekly Premium'},
    'monthly': {'price': 3000, 'duration': 30, 'name': 'Monthly Premium'}
}

# Email configuration for OTP
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'aliyuhaydal9@gmail.com',  # Change this
    'sender_password': 'ukvxnwmvyfjakmnh'   # Change this
}

# =============================================
# ENHANCED USER AUTHENTICATION SYSTEM
# =============================================

# File-based database for persistence
USERS_FILE = 'users.json'
PAYMENTS_FILE = 'payments.json'
SESSIONS_FILE = 'sessions.json'
OTP_STORAGE_FILE = 'otp_storage.json'

class Database:
    # Use in-memory storage for Vercel (no file writing)
    _users_cache = {}
    _payments_cache = {}
    _sessions_cache = {}
    _otp_cache = {}
    
    @staticmethod
    def load_users():
        try:
            # Try to load from file first (for initial data)
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r') as f:
                    initial_data = json.load(f)
                    Database._users_cache.update(initial_data)
            return Database._users_cache
        except:
            return Database._users_cache
    
    @staticmethod
    def save_users(users):
        # VERCEL FIX: Don't write to file system
        print(f"DEBUG: Would save {len(users)} users (file writing disabled on Vercel)")
        # Don't write to file on Vercel
        return True
    
    @staticmethod
    def load_payments():
        try:
            if os.path.exists(PAYMENTS_FILE):
                with open(PAYMENTS_FILE, 'r') as f:
                    initial_data = json.load(f)
                    Database._payments_cache.update(initial_data)
            return Database._payments_cache
        except:
            return Database._payments_cache
    
    @staticmethod
    def save_payments(payments):
        print(f"DEBUG: Would save {len(payments)} payments (file writing disabled)")
        return True
    
    @staticmethod
    def load_sessions():
        try:
            if os.path.exists(SESSIONS_FILE):
                with open(SESSIONS_FILE, 'r') as f:
                    initial_data = json.load(f)
                    Database._sessions_cache.update(initial_data)
            return Database._sessions_cache
        except:
            return Database._sessions_cache
    
    @staticmethod
    def save_sessions(sessions):
        print(f"DEBUG: Would save {len(sessions)} sessions (file writing disabled)")
        return True
    
    @staticmethod
    def load_otp_storage():
        try:
            if os.path.exists(OTP_STORAGE_FILE):
                with open(OTP_STORAGE_FILE, 'r') as f:
                    initial_data = json.load(f)
                    Database._otp_cache.update(initial_data)
            return Database._otp_cache
        except:
            return Database._otp_cache
    
    @staticmethod
    def save_otp_storage(otp_storage):
        print(f"DEBUG: Would save OTP data (file writing disabled)")
        return True

class EmailService:
    @staticmethod
    def send_otp_email(recipient_email, otp_code):
        """Send OTP code to user's email"""
        try:
            # For demo purposes, we'll just print the OTP
            print(f"📧 OTP for {recipient_email}: {otp_code}")
            
            # Uncomment for real email sending:
            msg = MIMEMultipart()  # FIXED: MimeMultipart → MIMEMultipart
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = recipient_email
            msg['Subject'] = "CyberGuard NG - Email Verification OTP"
            
            body = f"""<h2>CyberGuard NG Email Verification</h2>
            <p>Your OTP code is: <strong>{otp_code}</strong></p>
            <p>This code will expire in 10 minutes.</p>
            <br>
            <p>Best regards,<br>CyberGuard NG Team</p>"""
            
            msg.attach(MIMEText(body, 'html'))  # FIXED: MimeText → MIMEText
            
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False

class AuthManager:
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password, hashed):
        return AuthManager.hash_password(password) == hashed
    
    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def generate_session_token():
        return secrets.token_hex(32)
    
    @staticmethod
    def create_session(user_id):
        sessions = Database.load_sessions()
        session_token = AuthManager.generate_session_token()
        
        session_data = {
            'user_id': user_id,
            'ip_address': request.remote_addr,  # SECURITY ENHANCEMENT
            'user_agent': request.headers.get('User-Agent', ''),
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=30)).isoformat(),
            'last_accessed': datetime.now().isoformat()
        }
        
        sessions[session_token] = session_data
        Database.save_sessions(sessions)
        return session_token
    
    @staticmethod
    def validate_session(session_token):
        sessions = Database.load_sessions()
        if session_token in sessions:
            session_data = sessions[session_token]
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            
            # SECURITY ENHANCEMENTS:
            # 1. Check if session expired
            if datetime.now() > expires_at:
                del sessions[session_token]
                Database.save_sessions(sessions)
                return None
            
            # 2. Check IP address (prevent session hijacking)
            if session_data.get('ip_address') != request.remote_addr:
                # IP changed - security risk, invalidate session
                del sessions[session_token]
                Database.save_sessions(sessions)
                return None
            
            # 3. Update last accessed time
            session_data['last_accessed'] = datetime.now().isoformat()
            sessions[session_token] = session_data
            Database.save_sessions(sessions)
            
            return session_data['user_id']
        return None
    
    @staticmethod
    def logout_session(session_token):
        sessions = Database.load_sessions()
        if session_token in sessions:
            del sessions[session_token]
            Database.save_sessions(sessions)
            return True
        return False
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions (run periodically)"""
        sessions = Database.load_sessions()
        current_time = datetime.now()
        expired_count = 0
        
        for session_token, session_data in list(sessions.items()):
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if current_time > expires_at:
                del sessions[session_token]
                expired_count += 1
        
        if expired_count > 0:
            Database.save_sessions(sessions)
            print(f"🧹 Cleaned up {expired_count} expired sessions")
        
        return expired_count
    
    @staticmethod
    def get_session_info(session_token):
        """Get session information for admin/debug purposes"""
        sessions = Database.load_sessions()
        if session_token in sessions:
            return sessions[session_token]
        return None

class UserManager:
    @staticmethod
    def create_user(email, password, phone_number, name=None):
        users = Database.load_users()
        user_id = 'user_' + str(int(datetime.now().timestamp()))
        
        # Check if email already exists
        for existing_user in users.values():
            if existing_user.get('email') == email:
                return None, "Email already registered"
        
        user_data = {
            'id': user_id,
            'email': email,
            'password_hash': AuthManager.hash_password(password),
            'phone_number': phone_number,
            'name': name,
            'is_verified': False,
            'is_premium': False,
            'premium_until': None,
            'premium_plan': None,
            'checks_today': 0,
            'last_check_date': str(datetime.now().date()),
            'total_checks': 0,
            'payment_pending': False,
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
        }
        
        users[user_id] = user_data
        Database.save_users(users)
        return user_data, None
    
    @staticmethod
    def authenticate_user(email, password):
        users = Database.load_users()
        for user in users.values():
            if user.get('email') == email and AuthManager.verify_password(password, user['password_hash']):
                # Update last login
                user['last_login'] = datetime.now().isoformat()
                users[user['id']] = user
                return user
        return None
    
    @staticmethod
    def get_user(user_id):
        users = Database.load_users()
        if user_id in users:
            # Update last active
            users[user_id]['last_active'] = datetime.now().isoformat()
            Database.save_users(users)
            return users[user_id]
        return None
    
    @staticmethod
    def verify_user_email(user_id):
        users = Database.load_users()
        if user_id in users:
            users[user_id]['is_verified'] = True
            Database.save_users(users)
            return True
        return False
    
    @staticmethod
    def save_user(user):
        users = Database.load_users()
        users[user['id']] = user
        Database.save_users(users)
    
    @staticmethod
    def get_all_users():
        return Database.load_users()
    
    @staticmethod
    def can_make_free_check(user):
        if not user:
            return False
            
        today = str(datetime.now().date())
        if user.get('last_check_date') != today:
            user['checks_today'] = 0
            user['last_check_date'] = today
        
        # Premium users have unlimited checks
        if user['is_premium'] and user.get('premium_until'):
            premium_until = datetime.strptime(user['premium_until'], '%Y-%m-%d').date() if isinstance(user['premium_until'], str) else user['premium_until']
            if datetime.now().date() > premium_until:
                user['is_premium'] = False
                user['premium_until'] = None
                user['premium_plan'] = None
            else:
                return True
        
        return user['checks_today'] < 5
    
    @staticmethod
    def record_check(user):
        user['checks_today'] += 1
        user['total_checks'] += 1
        user['last_check_date'] = str(datetime.now().date())
        UserManager.save_user(user)
    
    @staticmethod
    def activate_premium(user, plan_type):
        user['is_premium'] = True
        user['premium_plan'] = plan_type
        plan_duration = PRICING_PLANS[plan_type]['duration']
        user['premium_until'] = str((datetime.now() + timedelta(days=plan_duration)).date())
        user['payment_pending'] = False
        UserManager.save_user(user)
        return user

class OTPManager:
    @staticmethod
    def generate_and_send_otp(email):
        otp_storage = Database.load_otp_storage()
        otp_code = AuthManager.generate_otp()
        
        otp_data = {
            'otp_code': otp_code,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(minutes=10)).isoformat(),
            'verified': False
        }
        
        otp_storage[email] = otp_data
        Database.save_otp_storage(otp_storage)
        
        # Send OTP via email
        return EmailService.send_otp_email(email, otp_code)
    
    @staticmethod
    def verify_otp(email, otp_code):
        otp_storage = Database.load_otp_storage()
        if email in otp_storage:
            otp_data = otp_storage[email]
            expires_at = datetime.fromisoformat(otp_data['expires_at'])
            
            if datetime.now() < expires_at and otp_data['otp_code'] == otp_code:
                otp_data['verified'] = True
                otp_storage[email] = otp_data
                Database.save_otp_storage(otp_storage)
                return True
        return False
    
    @staticmethod
    def is_verified(email):
        otp_storage = Database.load_otp_storage()
        if email in otp_storage:
            return otp_storage[email].get('verified', False)
        return False

class PaymentManager:
    @staticmethod
    def create_payment(user_id, plan_type, phone_number, name=None):
        payments = Database.load_payments()
        payment_id = f"pay_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        payment = {
            'id': payment_id,
            'user_id': user_id,
            'plan_type': plan_type,
            'phone_number': phone_number,
            'name': name,
            'amount': PRICING_PLANS[plan_type]['price'],
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'verified_at': None
        }
        
        payments[payment_id] = payment
        Database.save_payments(payments)
        
        # Update user to show payment pending
        user = UserManager.get_user(user_id)
        if user:
            user['payment_pending'] = True
            if name and not user.get('name'):
                user['name'] = name
            UserManager.save_user(user)
        
        return payment
    
    @staticmethod
    def get_payment(payment_id):
        payments = Database.load_payments()
        return payments.get(payment_id)
    
    @staticmethod
    def update_payment(payment_id, updates):
        payments = Database.load_payments()
        if payment_id in payments:
            payments[payment_id].update(updates)
            Database.save_payments(payments)
            return True
        return False
    
    @staticmethod
    def get_all_payments():
        return Database.load_payments()

# Initialize databases
for file in [USERS_FILE, PAYMENTS_FILE, SESSIONS_FILE, OTP_STORAGE_FILE]:
    if not os.path.exists(file):
        if file == USERS_FILE:
            Database.save_users({})
        elif file == PAYMENTS_FILE:
            Database.save_payments({})
        elif file == SESSIONS_FILE:
            Database.save_sessions({})
        elif file == OTP_STORAGE_FILE:
            Database.save_otp_storage({})

@app.route('/')
def home():
    return r'''
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
            background: linear-gradient(135deg, \#667eea 0%, \#764ba2 100%);
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
        input, textarea, select {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus, textarea:focus, select:focus {
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
        .btn-info {
            background: linear-gradient(135deg, #17a2b8, #138496);
        }
        .btn-warning {
            background: linear-gradient(135deg, #ffc107, #e0a800);
            color: #000;
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
        .payment-section {
            background: #e7f3ff;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .bank-details {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #28a745;
        }
        .registration-section {
            background: #e7f3ff;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .login-section {
            background: #e7f3ff;
            border: 2px solid #007bff;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .otp-section {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .user-menu {
            position: absolute;
            top: 20px;
            right: 20px;
            background: white;
            padding: 10px 15px;
            border-radius: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        @media (max-width: 768px) {
            .pricing-cards { flex-direction: column; }
            .tabs { flex-direction: column; }
            .user-menu { position: relative; top: 0; right: 0; margin: 10px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ CyberGuard NG <span class="premium-badge">PREMIUM</span></h1>
            <p>Advanced Nigerian Fraud Protection with Premium Features</p>
        </div>
        
        <div id="userMenu" class="user-menu" style="display: none;">
            <span id="userGreeting"></span>
            <button class="btn" onclick="logout()" style="padding: 5px 10px; margin-left: 10px; width: auto;">Logout</button>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('scanner')">Security Scanner</button>
            <button class="tab" onclick="switchTab('register')">Register</button>
            <button class="tab" onclick="switchTab('verify')">Verify Email</button>
            <button class="tab" onclick="switchTab('login')">Login</button>
            <button class="tab" onclick="switchTab('premium')">Go Premium</button>
            <button class="tab" onclick="switchTab('account')">My Account</button>
            <button class="tab" onclick="switchTab('admin')">Admin</button>
        </div>
        
        <!-- SCANNER TAB -->
        <div id="scanner-content" class="tab-content active">
            <div class="user-stats" id="userStats">
                <strong>Account:</strong> <span id="accountType">Free</span> | 
                <strong>Checks Today:</strong> <span id="checksCount">0</span>/<span id="maxChecks">5</span>
                <span id="premiumInfo" style="display: none;">| <strong>Premium Until:</strong> <span id="premiumUntil"></span></span>
            </div>
            
            <div id="notLoggedInWarning" class="result warning">
                <strong>⚠️ Please Login First!</strong><br>
                You need to login to use the security scanner. Click the "Login" tab.
            </div>
            
            <div id="scannerContent" style="display: none;">
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
            </div>
            
            <div id="result" class="result">Ready to protect you from Nigerian fraud...</div>
        </div>
        
        <!-- REGISTER TAB -->
        <div id="register-content" class="tab-content">
            <h2>Register for CyberGuard NG</h2>
            <p>Create your account to start protecting yourself from fraud</p>
            
            <div class="registration-section">
                <div class="input-group">
                    <input type="text" id="userName" placeholder="Your Full Name">
                </div>
                <div class="input-group">
                    <input type="email" id="userEmail" placeholder="Your Email Address (Required)" required>
                </div>
                <div class="input-group">
                    <input type="password" id="userPassword" placeholder="Password (Minimum 6 characters)" required>
                </div>
                <div class="input-group">
                    <input type="password" id="userConfirmPassword" placeholder="Confirm Password" required>
                </div>
                <div class="input-group">
                    <input type="text" id="userPhone" placeholder="Your WhatsApp Number (Required)" required>
                </div>
                <button class="btn btn-premium" onclick="registerUser()">Create Account & Send OTP</button>
            </div>
            
            <div id="otpVerificationSection" class="otp-section" style="display: none;">
                <h3>📧 Verify Your Email</h3>
                <p>We sent a 6-digit OTP code to your email</p>
                <div class="input-group">
                    <input type="text" id="otpCode" placeholder="Enter 6-digit OTP code" maxlength="6">
                </div>
                <button class="btn btn-warning" onclick="verifyOTP()">Verify OTP</button>
                <button class="btn" onclick="resendOTP()" style="margin-top: 10px;">Resend OTP</button>
            </div>
            
            <div id="registrationSuccess" style="display: none;">
                <div class="result safe">
                    <h3>🎉 Registration Successful!</h3>
                    <p><strong>Your User ID:</strong> <span id="newUserId"></span></p>
                    <p><strong>Email:</strong> <span id="newUserEmail"></span></p>
                    <p>Your account has been verified and is ready to use!</p>
                    <button class="btn" onclick="switchTab('scanner')">Start Scanning Now</button>
                </div>
            </div>
        </div>
        <!-- VERIFY EMAIL TAB -->
<div id="verify-content" class="tab-content">
    <h2>Verify Your Email</h2>
    <p>Already registered but didn't verify your email? Get a new OTP code here.</p>
    
    <div class="registration-section">
        <div class="input-group">
            <input type="email" id="verifyEmail" placeholder="Enter your registered email" required>
        </div>
        <button class="btn btn-premium" onclick="sendVerificationOTP()">Send New OTP Code</button>
    </div>
    
    <div id="verifyOtpSection" class="otp-section" style="display: none;">
        <h3>📧 Enter OTP Code</h3>
        <p>We sent a 6-digit OTP code to your email</p>
        <div class="input-group">
            <input type="text" id="verifyOtpCode" placeholder="Enter 6-digit OTP code" maxlength="6">
        </div>
        <button class="btn btn-warning" onclick="verifyExistingUserOTP()">Verify OTP</button>
        <button class="btn" onclick="resendVerificationOTP()" style="margin-top: 10px;">Resend OTP</button>
    </div>
    
    <div id="verifySuccess" style="display: none;">
        <div class="result safe">
            <h3>🎉 Email Verified Successfully!</h3>
            <p>Your email has been verified. You can now login and use all features.</p>
            <button class="btn" onclick="switchTab('login')">Login Now</button>
        </div>
    </div>
</div>
        
        <!-- LOGIN TAB -->
        <div id="login-content" class="tab-content">
            <h2>Login to Your Account</h2>
            <p>Access your CyberGuard NG account</p>
            
            <div class="login-section">
                <div class="input-group">
                    <input type="email" id="loginEmail" placeholder="Your Email Address">
                </div>
                <div class="input-group">
                    <input type="password" id="loginPassword" placeholder="Your Password">
                </div>
                <button class="btn btn-premium" onclick="loginUser()">Login to Account</button>
            </div>
            
            <div style="text-align: center; margin-top: 20px;">
                <p>Don't have an account? <a href="javascript:void(0)" onclick="switchTab('register')">Register here</a></p>
            </div>
        </div>
        
        <!-- PREMIUM TAB -->
        <div id="premium-content" class="tab-content">
            <h2>Upgrade to CyberGuard Premium</h2>
            <p>Get advanced protection and unlimited scans</p>
            
            <div id="premiumNotLoggedIn" class="result warning">
                <strong>Please Login First!</strong><br>
                You need to login before upgrading to premium.
            </div>
            
            <div id="premiumContent" style="display: none;">
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
                            <li>✓ 24 hours access</li>
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
                            <li>✓ Best value</li>
                        </ul>
                        <button class="btn btn-premium" onclick="showPaymentForm('weekly')">Get Weekly Premium</button>
                    </div>
                </div>
                
                <div id="paymentSection" class="payment-section" style="display: none;">
                    <h3>Complete Your Payment</h3>
                    
                    <div id="paymentDetails"></div>
                    
                    <div class="bank-details">
                        <h4>🏦 Bank Transfer Details:</h4>
                        <p><strong>Bank:</strong> ZenithBank</p>
                        <p><strong>Account Number:</strong> 4249996702</p>
                        <p><strong>Account Name:</strong> Aliyu Egwa Usman</p>
                        <p><strong>Amount:</strong> <span id="paymentAmount">₦0</span></p>
                    </div>
                    
                    <button class="btn btn-premium" onclick="initiatePayment()">Get Payment Instructions</button>
                    
                    <div id="paymentInstructions" style="display: none; margin-top: 20px;">
                        <div class="bank-details">
                            <h4>💰 Payment Successfully Initiated!</h4>
                            <p><strong>Payment ID:</strong> <span id="paymentIdDisplay"></span></p>
                            <p><strong>Next Steps:</strong></p>
                            <ol>
                                <li>Complete bank transfer with details above</li>
                                <li>Take screenshot of payment confirmation</li>
                                <li>WhatsApp screenshot to: <strong>09031769476</strong></li>
                                <li>Include your Payment ID in the message</li>
                            </ol>
                            <p>We'll activate your premium within 1 hour of payment verification!</p>
                        </div>
                        <button class="btn" onclick="checkPaymentStatus()" style="margin-top: 15px;">Check Payment Status</button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- ACCOUNT TAB -->
        <div id="account-content" class="tab-content">
            <h2>My Account</h2>
            
            <div id="accountNotLoggedIn" class="result warning">
                <strong>Please Login First!</strong><br>
                You need to login to view your account details.
            </div>
            
            <div id="accountContent" style="display: none;">
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <p><strong>User ID:</strong> <span id="accountUserId"></span></p>
                    <p><strong>Name:</strong> <span id="accountName">Not provided</span></p>
                    <p><strong>Email:</strong> <span id="accountEmail"></span></p>
                    <p><strong>Phone:</strong> <span id="accountPhone"></span></p>
                    <p><strong>Status:</strong> <span id="accountStatus">Free User</span></p>
                    <p><strong>Email Verified:</strong> <span id="accountVerified">No</span></p>
                    <p><strong>Checks Today:</strong> <span id="accountChecks">0</span>/<span id="accountMaxChecks">5</span></p>
                    <p><strong>Total Checks:</strong> <span id="totalChecks">0</span></p>
                    <div id="premiumAccountInfo" style="display: none;">
                        <p><strong>Premium Plan:</strong> <span id="premiumPlan"></span></p>
                        <p><strong>Premium Until:</strong> <span id="premiumUntilDate"></span></p>
                    </div>
                    <button class="btn btn-premium" onclick="switchTab('premium')">Upgrade to Premium</button>
                </div>
            </div>
        </div>
        
        <!-- ADMIN TAB -->
        <div id="admin-content" class="tab-content">
            <h2>Admin Panel</h2>
            <p>Manage users and activate premiums</p>
            
            <div class="input-group">
                <input type="password" id="adminPassword" placeholder="Enter Admin Password">
                <button class="btn btn-info" onclick="loginAdmin()">Access Admin Panel</button>
            </div>
            
            <div id="adminPanel" style="display: none;">
                <h3>User Management</h3>
                <button class="btn" onclick="loadAllUsers()">Refresh Users List</button>
                <div id="usersList" style="margin-top: 20px;"></div>
                
                <h3>Payment Management</h3>
                <button class="btn" onclick="loadAllPayments()">Refresh Payments</button>
                <div id="paymentsList" style="margin-top: 20px;"></div>
                
                <h3>Manual Premium Activation</h3>
                <div class="input-group">
                    <input type="text" id="activateUserId" placeholder="User ID to activate">
                    <select id="activatePlan">
                        <option value="daily">Daily Premium</option>
                        <option value="weekly">Weekly Premium</option>
                        <option value="monthly">Monthly Premium</option>
                    </select>
                    <button class="btn btn-premium" onclick="manualActivatePremium()">Activate Premium</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentUser = null;
        let currentSession = null;
        let selectedPlan = null;
        let currentPaymentId = null;
        let isAdmin = false;
        let pendingEmail = null;
        
        document.addEventListener('DOMContentLoaded', function() {
            checkExistingSession();
        });
        
        function checkExistingSession() {
            const savedSession = localStorage.getItem('cyberguard_session');
            if (savedSession) {
                validateSession(savedSession);
            } else {
                showNotLoggedInUI();
            }
        }
        
        async function validateSession(sessionToken) {
            try {
                const response = await fetch('/api/validate-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_token: sessionToken })
                });
                
                const result = await response.json();
                if (result.success) {
                    currentSession = sessionToken;
                    currentUser = result.user_id;
                    showLoggedInUI();
                    loadUserStats();
                } else {
                    localStorage.removeItem('cyberguard_session');
                    showNotLoggedInUI();
                }
            } catch (error) {
                showNotLoggedInUI();
            }
        }
        // Clear form after successful registration
function clearRegistrationForm() {
    document.getElementById('userName').value = '';
    document.getElementById('userEmail').value = '';
    document.getElementById('userPassword').value = '';
    document.getElementById('userConfirmPassword').value = '';
    document.getElementById('userPhone').value = '';
}

// Clear form after successful login
function clearLoginForm() {
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
}

// Clear OTP form after successful verification
function clearOtpForm() {
    document.getElementById('otpCode').value = '';
    document.getElementById('verifyOtpCode').value = '';
}
        
        function showLoggedInUI() {
            document.getElementById('userMenu').style.display = 'block';
            document.getElementById('userGreeting').textContent = `Welcome!`;
            document.getElementById('scannerContent').style.display = 'block';
            document.getElementById('notLoggedInWarning').style.display = 'none';
            document.getElementById('premiumContent').style.display = 'block';
            document.getElementById('premiumNotLoggedIn').style.display = 'none';
            document.getElementById('accountContent').style.display = 'block';
            document.getElementById('accountNotLoggedIn').style.display = 'none';
        }
        
        function showNotLoggedInUI() {
            document.getElementById('userMenu').style.display = 'none';
            document.getElementById('scannerContent').style.display = 'none';
            document.getElementById('notLoggedInWarning').style.display = 'block';
            document.getElementById('premiumContent').style.display = 'none';
            document.getElementById('premiumNotLoggedIn').style.display = 'block';
            document.getElementById('accountContent').style.display = 'none';
            document.getElementById('accountNotLoggedIn').style.display = 'block';
        }
        
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabName + '-content').classList.add('active');
            
            if (tabName === 'account' && currentUser) {
                updateAccountInfo();
            }
        }
        
        async function registerUser() {
            const email = document.getElementById('userEmail').value;
            const password = document.getElementById('userPassword').value;
            const confirmPassword = document.getElementById('userConfirmPassword').value;
            const phone = document.getElementById('userPhone').value;
            const name = document.getElementById('userName').value;
            
            if (!email || !password || !phone) {
                alert('Please fill in all required fields');
                return;
            }
            
            if (password !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }
            
            if (password.length < 6) {
                alert('Password must be at least 6 characters long');
                return;
            }
            
            if (!phone.startsWith('0') || phone.length !== 11) {
                alert('Please enter a valid Nigerian phone number (11 digits starting with 0)');
                return;
            }
            
            try {
                const response = await fetch('/api/register-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        email: email,
                        password: password,
                        phone_number: phone,
                        name: name
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    pendingEmail = email;
                    document.getElementById('otpVerificationSection').style.display = 'block';
                    alert('OTP sent to your email! Please check your inbox.');
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please check your connection and try again.');
            }
        }
        
        async function verifyOTP() {
            const otpCode = document.getElementById('otpCode').value;
            
            if (!otpCode || otpCode.length !== 6) {
                alert('Please enter a valid 6-digit OTP code');
                return;
            }
            
            try {
                const response = await fetch('/api/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        email: pendingEmail,
                        otp_code: otpCode
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    // Auto-login after successful verification
                    currentSession = result.session_token;
                    currentUser = result.user_id;
                    localStorage.setItem('cyberguard_session', currentSession);
                    
                    document.getElementById('newUserId').textContent = result.user_id;
                    document.getElementById('newUserEmail').textContent = pendingEmail;
                    document.getElementById('registrationSuccess').style.display = 'block';
                    document.getElementById('otpVerificationSection').style.display = 'none';
                   
                    clearRegistrationForm();
                    clearOtpForm();
                   
                    showLoggedInUI();
                    loadUserStats();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }
        
        async function resendOTP() {
            if (!pendingEmail) {
                alert('No email found. Please start registration again.');
                return;
            }
            
            try {
                const response = await fetch('/api/resend-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: pendingEmail })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('New OTP sent to your email!');
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }
        // Send OTP for existing unverified users
async function sendVerificationOTP() {
    const email = document.getElementById('verifyEmail').value;
    
    if (!email) {
        alert('Please enter your email address');
        return;
    }
    
    try {
        const response = await fetch('/api/send-verification-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        });
        
        const result = await response.json();
        if (result.success) {
            pendingEmail = email;
            document.getElementById('verifyOtpSection').style.display = 'block';
            alert('New OTP sent to your email! Please check your inbox.');
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        alert('Network error. Please check your connection and try again.');
    }
}

// Verify OTP for existing users
async function verifyExistingUserOTP() {
    const otpCode = document.getElementById('verifyOtpCode').value;
    
    if (!otpCode || otpCode.length !== 6) {
        alert('Please enter a valid 6-digit OTP code');
        return;
    }
    
    try {
        const response = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                email: pendingEmail,
                otp_code: otpCode
            })
        });
        
        const result = await response.json();
        if (result.success) {
            document.getElementById('verifySuccess').style.display = 'block';
            document.getElementById('verifyOtpSection').style.display = 'none';
            
            alert('🎉 Email verified successfully! You can now login.');
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        alert('Network error. Please try again.');
    }
}

// Resend OTP for existing users
async function resendVerificationOTP() {
    if (!pendingEmail) {
        alert('No email found. Please enter your email first.');
        return;
    }
    
    try {
        const response = await fetch('/api/resend-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: pendingEmail })
        });
        
        const result = await response.json();
        if (result.success) {
            alert('New OTP sent to your email!');
        } else {
            alert('Error: ' + result.message);
        }
    } catch (error) {
        alert('Network error. Please try again.');
    }
}
        
         async function loginUser() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!email || !password) {
        alert('Please enter both email and password');
        return;
    }
    
    try {
        const response = await fetch('/api/login-user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                email: email,
                password: password
            })
        });
        
        const result = await response.json();
        if (result.success) {
            currentSession = result.session_token;
            currentUser = result.user_id;
            localStorage.setItem('cyberguard_session', currentSession);
            
            clearLoginForm();
            
            showLoggedInUI();
            loadUserStats();
            switchTab('scanner');
            
            // Show success message
            showResult({
                message: '✅ Login successful! Welcome back.',
                type: 'safe'
            });
            
        } else {
            // Handle email verification required
            if (result.needs_verification) {
                alert('📧 ' + result.message);
                
                // Pre-fill email in registration form and show OTP section
                pendingEmail = email;
                switchTab('register');
                document.getElementById('userEmail').value = email;
                document.getElementById('userEmail').readOnly = true; // Prevent changing email
                document.getElementById('otpVerificationSection').style.display = 'block';
                
                // Scroll to OTP section
                document.getElementById('otpVerificationSection').scrollIntoView({ 
                    behavior: 'smooth' 
                });
                
                // Show helpful message
                showResult({
                    message: '📧 Please verify your email to continue. OTP section is now available.',
                    type: 'warning'
                });
                
            } else {
                // Regular login error
                alert('Error: ' + result.message);
                showResult({
                    message: '❌ ' + result.message,
                    type: 'warning'
                });
            }
        }
    } catch (error) {
        alert('Network error. Please check your connection and try again.');
        showResult({
            message: '❌ Network error. Please check your connection.',
            type: 'warning'
        });
    }
}
        
        async function logout() {
            if (currentSession) {
                await fetch('/api/logout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_token: currentSession })
                });
            }
            
            currentSession = null;
            currentUser = null;
            localStorage.removeItem('cyberguard_session');
            showNotLoggedInUI();
            switchTab('login');
        }
        
        async function loadUserStats() {
            if (!currentUser) return;
            
            try {
                const response = await fetch('/api/user-stats?user_id=' + currentUser);
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                console.log('Error loading user stats');
            }
        }
        
        function updateUI(stats) {
            if (!currentUser) return;
            
            const isPremium = stats.is_premium;
            const maxChecks = isPremium ? '∞' : '5';
            
            document.getElementById('checksCount').textContent = stats.checks_today;
            document.getElementById('maxChecks').textContent = maxChecks;
            document.getElementById('accountType').textContent = isPremium ? 'Premium 🏆' : 'Free';
            document.getElementById('accountChecks').textContent = stats.checks_today;
            document.getElementById('accountMaxChecks').textContent = maxChecks;
            document.getElementById('totalChecks').textContent = stats.total_checks;
            document.getElementById('accountStatus').textContent = isPremium ? 'Premium User 🏆' : 'Free User';
            document.getElementById('accountUserId').textContent = currentUser;
            document.getElementById('accountPhone').textContent = stats.phone_number || 'Not provided';
            document.getElementById('accountName').textContent = stats.name || 'Not provided';
            document.getElementById('accountEmail').textContent = stats.email || 'Not provided';
            document.getElementById('accountVerified').textContent = stats.is_verified ? 'Yes ✅' : 'No ❌';
            
            if (isPremium && stats.premium_until) {
                document.getElementById('premiumInfo').style.display = 'inline';
                document.getElementById('premiumUntil').textContent = stats.premium_until;
                document.getElementById('premiumAccountInfo').style.display = 'block';
                document.getElementById('premiumPlan').textContent = stats.premium_plan || 'Premium';
                document.getElementById('premiumUntilDate').textContent = stats.premium_until;
            } else {
                document.getElementById('premiumInfo').style.display = 'none';
                document.getElementById('premiumAccountInfo').style.display = 'none';
            }
        }
        
        function updateAccountInfo() {
            loadUserStats();
        }
        
         async function checkUSSD() {
    if (!currentUser) {
        alert('Please login first');
        switchTab('login');
        return;
    }
    
    const code = document.getElementById('ussdInput').value;
    if (!code) return;
    
    try {
        const response = await fetch('/api/check-ussd', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code, user_id: currentUser })
        });
        
        const result = await response.json();
        
        // Handle email verification requirement
        if (result.needs_verification) {
            alert('📧 ' + result.message);
            switchTab('register');
            return;
        }
        
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
    if (!currentUser) {
        alert('Please login first');
        switchTab('login');
        return;
    }
    
    const sms = document.getElementById('smsInput').value;
    if (!sms) return;
    
    try {
        const response = await fetch('/api/check-sms', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sms: sms, user_id: currentUser })
        });
        
        const result = await response.json();
        
        // Handle email verification requirement
        if (result.needs_verification) {
            alert('📧 ' + result.message);
            switchTab('register');
            return;
        }
        
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
            if (!currentUser) {
                alert('Please login first');
                switchTab('login');
                return;
            }
            
            selectedPlan = plan;
            document.getElementById('paymentSection').style.display = 'block';
            document.getElementById('paymentInstructions').style.display = 'none';
            
            const plans = {
                'daily': { price: 200, name: 'Daily Premium (24 hours)' },
                'weekly': { price: 1000, name: 'Weekly Premium (7 days)' }
            };
            
            const planInfo = plans[plan];
            document.getElementById('paymentDetails').innerHTML = `
                <p><strong>Selected Plan:</strong> ${planInfo.name}</p>
                <p><strong>Amount to Pay:</strong> ₦${planInfo.price}</p>
            `;
            document.getElementById('paymentAmount').textContent = `₦${planInfo.price}`;
        }
        
        async function initiatePayment() {
            if (!currentUser) {
                alert('Please login first');
                return;
            }
            
            try {
                const userStats = await (await fetch('/api/user-stats?user_id=' + currentUser)).json();
                
                const response = await fetch('/api/initiate-payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        user_id: currentUser, 
                        plan_type: selectedPlan,
                        phone_number: userStats.phone_number,
                        name: userStats.name
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    currentPaymentId = result.payment_id;
                    document.getElementById('paymentIdDisplay').textContent = result.payment_id;
                    document.getElementById('paymentInstructions').style.display = 'block';
                    
                    document.getElementById('paymentInstructions').scrollIntoView({ behavior: 'smooth' });
                    
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please check your connection and try again.');
            }
        }
        
        async function checkPaymentStatus() {
            if (!currentPaymentId || !currentUser) {
                alert('No payment found. Please initiate a payment first.');
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
                    } else if (result.payment_status === 'pending') {
                        alert('Payment is still pending. We are verifying your payment. Please wait or contact us on WhatsApp.');
                    } else {
                        alert('Payment status: ' + result.payment_status);
                    }
                } else {
                    alert('Error checking payment: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }
        
        // Admin functions
        async function loginAdmin() {
            const password = document.getElementById('adminPassword').value;
            if (password === '0701805Aliyu@@') {
                isAdmin = true;
                document.getElementById('adminPanel').style.display = 'block';
                loadAllUsers();
                loadAllPayments();
            } else {
                alert('Invalid admin password');
            }
        }
        
        async function loadAllUsers() {
            if (!isAdmin) return;
            
            try {
                const response = await fetch('/api/admin/users');
                const users = await response.json();
                
                let html = '<div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">';
                html += '<table style="width: 100%; border-collapse: collapse;">';
                html += '<tr style="background: #007bff; color: white;"><th>User ID</th><th>Email</th><th>Phone</th><th>Status</th><th>Verified</th><th>Actions</th></tr>';
                
                Object.values(users).forEach(user => {
                    html += `<tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px; font-size: 12px;">${user.id}</td>
                        <td>${user.email || 'N/A'}</td>
                        <td>${user.phone_number || 'N/A'}</td>
                        <td>${user.is_premium ? 'Premium' : 'Free'}</td>
                        <td>${user.is_verified ? 'Yes' : 'No'}</td>
                        <td><button onclick="activateUserPremium('${user.id}')" class="btn" style="padding: 5px; font-size: 12px;">Activate Premium</button></td>
                    </tr>`;
                });
                
                html += '</table></div>';
                document.getElementById('usersList').innerHTML = html;
            } catch (error) {
                console.error('Error loading users:', error);
            }
        }
        
        async function loadAllPayments() {
            if (!isAdmin) return;
            
            try {
                const response = await fetch('/api/admin/payments');
                const payments = await response.json();
                
                let html = '<div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px;">';
                html += '<table style="width: 100%; border-collapse: collapse;">';
                html += '<tr style="background: #28a745; color: white;"><th>Payment ID</th><th>User ID</th><th>Plan</th><th>Amount</th><th>Status</th><th>Actions</th></tr>';
                
                Object.values(payments).forEach(payment => {
                    html += `<tr style="border-bottom: 1px solid #ddd;">
                        <td style="padding: 8px; font-size: 12px;">${payment.id}</td>
                        <td style="font-size: 12px;">${payment.user_id}</td>
                        <td>${payment.plan_type}</td>
                        <td>₦${payment.amount}</td>
                        <td>${payment.status}</td>
                        <td>
                            ${payment.status === 'pending' ? 
                                `<button onclick="verifyPayment('${payment.id}')" class="btn" style="padding: 5px; font-size: 12px;">Verify</button>` : 
                                'Verified'
                            }
                        </td>
                    </tr>`;
                });
                
                html += '</table></div>';
                document.getElementById('paymentsList').innerHTML = html;
            } catch (error) {
                console.error('Error loading payments:', error);
            }
        }
        
        async function verifyPayment(paymentId) {
            if (!isAdmin) return;
            
            try {
                const response = await fetch('/api/admin/verify-payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ payment_id: paymentId })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Payment verified and premium activated!');
                    loadAllPayments();
                    loadAllUsers();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error');
            }
        }
        
        async function activateUserPremium(userId) {
            if (!isAdmin) return;
            
            const plan = document.getElementById('activatePlan').value;
            
            try {
                const response = await fetch('/api/admin/activate-premium', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        user_id: userId,
                        plan_type: plan
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Premium activated for user: ' + userId);
                    loadAllUsers();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error');
            }
        }
        
        async function manualActivatePremium() {
            if (!isAdmin) return;
            
            const userId = document.getElementById('activateUserId').value;
            const plan = document.getElementById('activatePlan').value;
            
            if (!userId) {
                alert('Please enter a User ID');
                return;
            }
            
            await activateUserPremium(userId);
        }
    </script>
</body>
</html>
    '''

# =============================================
# ENHANCED AUTHENTICATION API ENDPOINTS
# =============================================

@app.route('/api/register-user', methods=['POST'])
def api_register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    phone_number = data.get('phone_number')
    name = data.get('name')
    
    if not email or not password or not phone_number:
        return jsonify({'success': False, 'message': 'Email, password and phone number are required'})
    
    # Create user
    user, error = UserManager.create_user(email, password, phone_number, name)
    if error:
        return jsonify({'success': False, 'message': error})
    
    # Generate and send OTP
    if OTPManager.generate_and_send_otp(email):
        return jsonify({
            'success': True,
            'message': 'Registration successful! OTP sent to your email.'
        })
    else:
        return jsonify({
            'success': True,
            'message': 'Registration successful! But failed to send OTP. Please contact support.'
        })

@app.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp_code = data.get('otp_code')
    
    if not email or not otp_code:
        return jsonify({'success': False, 'message': 'Email and OTP code are required'})
    
    # Verify OTP
    if OTPManager.verify_otp(email, otp_code):
        # Find user by email and mark as verified
        users = Database.load_users()
        user = None
        for user_data in users.values():
            if user_data.get('email') == email:
                user = user_data
                break
        
        if user:
            UserManager.verify_user_email(user['id'])
            
            # Create session ONLY after verification
            session_token = AuthManager.create_session(user['id'])
            
            return jsonify({
                'success': True,
                'message': 'Email verified successfully!',
                'user_id': user['id'],
                'session_token': session_token
            })
        else:
            return jsonify({'success': False, 'message': 'User not found'})
    else:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP code'})

@app.route('/api/send-verification-otp', methods=['POST'])
def api_send_verification_otp():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    # Check if user exists
    users = Database.load_users()
    user_exists = False
    for user in users.values():
        if user.get('email') == email:
            user_exists = True
            # Check if already verified
            if user.get('is_verified', False):
                return jsonify({'success': False, 'message': 'Email is already verified'})
            break
    
    if not user_exists:
        return jsonify({'success': False, 'message': 'Email not found. Please register first.'})
    
    # Generate and send OTP
    if OTPManager.generate_and_send_otp(email):
        return jsonify({
            'success': True,
            'message': 'OTP sent to your email!'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to send OTP. Please try again.'
        })

@app.route('/api/resend-otp', methods=['POST'])
def api_resend_otp():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required'})
    
    if OTPManager.generate_and_send_otp(email):
        return jsonify({'success': True, 'message': 'New OTP sent to your email'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send OTP'})

@app.route('/api/login-user', methods=['POST'])
def api_login_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'})
    
    user = UserManager.authenticate_user(email, password)
    if user:
        # CHECK IF EMAIL IS VERIFIED
        if not user.get('is_verified', False):
            return jsonify({
                'success': False, 
                'message': 'Please verify your email first. Check your inbox for OTP.',
                'needs_verification': True
            })
        
        # Create session only if verified
        session_token = AuthManager.create_session(user['id'])
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'user_id': user['id'],
            'session_token': session_token
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password'})

@app.route('/api/validate-session', methods=['POST'])
def api_validate_session():
    data = request.get_json()
    session_token = data.get('session_token')
    
    user_id = AuthManager.validate_session(session_token)
    if user_id:
        return jsonify({
            'success': True,
            'user_id': user_id
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid or expired session'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    data = request.get_json()
    session_token = data.get('session_token')
    
    if AuthManager.logout_session(session_token):
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    else:
        return jsonify({'success': False, 'message': 'Logout failed'})

@app.route('/api/user-stats', methods=['GET'])
def api_user_stats():
    user_id = request.args.get('user_id', 'default')
    user = UserManager.get_user(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # Check if premium has expired
    if user['is_premium'] and user.get('premium_until'):
        premium_until = datetime.strptime(user['premium_until'], '%Y-%m-%d').date() if isinstance(user['premium_until'], str) else user['premium_until']
        if datetime.now().date() > premium_until:
            user['is_premium'] = False
            user['premium_until'] = None
            user['premium_plan'] = None
            UserManager.save_user(user)
    
    return jsonify({
        'is_premium': user['is_premium'],
        'premium_until': user.get('premium_until'),
        'premium_plan': user.get('premium_plan'),
        'checks_today': user['checks_today'],
        'total_checks': user['total_checks'],
        'payment_pending': user.get('payment_pending', False),
        'phone_number': user.get('phone_number'),
        'email': user.get('email'),
        'name': user.get('name'),
        'is_verified': user.get('is_verified', False)
    })

# [Previous API endpoints for check-ussd, check-sms, initiate-payment, etc. remain the same]
# ... (Include all the previous API endpoints from the earlier implementation)

@app.route('/api/check-ussd', methods=['POST'])
def api_check_ussd():
    data = request.get_json()
    code = data.get('code', '').strip()
    user_id = data.get('user_id', 'default')
    
    user = UserManager.get_user(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # ENFORCE EMAIL VERIFICATION
    if not user.get('is_verified', False):
        return jsonify({
            'success': False,
            'message': '❌ Please verify your email first to use security scanner.',
            'type': 'warning',
            'needs_verification': True
        })
    
    # Check free limit
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited checks.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # =============================================
    # ENHANCED USSD FRAUD DETECTION
    # =============================================
    
    # Verified safe Nigerian bank USSD codes
    safe_bank_codes = [
        '*901#', '*894#', '*737#', '*919#', '*822#', '*533#', 
        '*322#', '*326#', '*779#', '*989#', '*123#', '*500#',
        '*955#', '*833#', '*706#', '*909#', '*966#', '*482#',
        '*502#', '*503#', '*504#', '*505#', '*506#', '*507#'
    ]
    
    # High-risk scam patterns in USSD
    scam_indicators = {
        'password': 10, 'pin': 10, 'bvn': 15, 'winner': 12, 'won': 12,
        'prize': 12, 'lottery': 12, 'claim': 10, 'verification': 8,
        'confirm': 6, 'update': 6, 'recharge': 5, 'airtime': 4,
        'transfer': 5, 'balance': 3, 'customer': 3, 'care': 3
    }
    
    # Suspicious code patterns
    suspicious_patterns = [
        r'\*.*\*.*\*.*\*',  # Too many asterisks
        r'\*.*password.*\#',  # Contains password
        r'\*.*pin.*\#',       # Contains PIN
        r'\*.*bvn.*\#',       # Contains BVN
        r'\*[0-9\*]{15,}',    # Too long/complex
    ]
    
    code_lower = code.lower()
    risk_score = 0
    detected_patterns = []
    
    # Check against safe codes
    if code in safe_bank_codes:
        message = '✅ SAFE - Verified Nigerian bank USSD code'
        result_type = 'safe'
        premium_features = None
    
    else:
        # Check for scam indicators
        for indicator, points in scam_indicators.items():
            if indicator in code_lower:
                risk_score += points
                detected_patterns.append(indicator)
        
        # Check suspicious patterns
        for pattern in suspicious_patterns:
            if re.search(pattern, code_lower):
                risk_score += 8
                detected_patterns.append('suspicious_format')
        
        # Risk assessment
        if risk_score >= 20:
            message = '🚨 EXTREME RISK - USSD SCAM DETECTED! Do not dial!'
            result_type = 'scam'
        elif risk_score >= 15:
            message = '🚨 HIGH RISK - Likely fraudulent USSD code'
            result_type = 'scam'
        elif risk_score >= 10:
            message = '⚠️ SUSPICIOUS - Verify with your bank before using'
            result_type = 'warning'
        elif risk_score >= 5:
            message = '⚠️ CAUTION - Unknown USSD code, use carefully'
            result_type = 'warning'
        else:
            message = '✅ Likely safe USSD code'
            result_type = 'safe'
        
        # Premium features
        if user['is_premium']:
            premium_features = f'🔍 Premium Analysis: Risk Score {risk_score}/30 - Detected: {", ".join(detected_patterns)}'
        else:
            premium_features = 'Upgrade to Premium for detailed USSD code analysis'
    
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
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # ENFORCE EMAIL VERIFICATION
    if not user.get('is_verified', False):
        return jsonify({
            'success': False,
            'message': '❌ Please verify your email first to use security scanner.',
            'type': 'warning',
            'needs_verification': True
        })
    
    # Check free limit
    if not user['is_premium'] and not UserManager.can_make_free_check(user):
        return jsonify({
            'message': '❌ FREE LIMIT REACHED! Upgrade to Premium for unlimited scans.',
            'type': 'warning',
            'limit_reached': True
        })
    
    UserManager.record_check(user)
    
    # =============================================
    # ENHANCED NIGERIAN FRAUD DETECTION LOGIC
    # =============================================
    sms_lower = sms.lower()
    score = 0
    reasons = []
    
    # High-risk Nigerian scam patterns
    high_risk_patterns = {
        r'won\s*\d+[,.]?\d*\s*(million|thousand|billion|lakh|crore)': 15,
        r'congratulation(s)?!*\s*you\s+(won|have|are)': 12,
        r'prize\s*(money|award|winner)': 10,
        r'lottery|jackpot|raffle': 10,
        r'claim\s*(your|this|now|immediately)': 8,
        r'free\s*(money|airtime|data|gift)': 8,
        r'account\s*verification': 7,
        r'password\s*reset': 7,
        r'bvn\s*(verification|update|confirmation)': 15,  # Very high risk in Nigeria
        r'atm\s*card\s*(details|number|pin)': 15,
        r'ussd\s*code': 6,
        r'click\s*(link|here|below)': 6,
        r'http[s]?://|www\.|bit\.ly|tinyurl': 8,
        r'call\s*0[7-9][0-9]{8,}': 7,  # Nigerian phone numbers
        r'whatsapp\s*0[7-9][0-9]{8,}': 7,
        r'urgent|immediate|action\s*required': 5,
        r'limited\s*time|offer\s*expires': 5,
        r'account\s*(suspended|blocked|deactivated)': 8,
        r'security\s*breach|unauthorized': 7,
        r'customer\s*care\s*0[7-9][0-9]{8,}': 6,
    }
    
    # Check each pattern
    for pattern, points in high_risk_patterns.items():
        if re.search(pattern, sms_lower, re.IGNORECASE):
            score += points
            # Extract the matched pattern name
            pattern_name = pattern.replace('\\s*', ' ').replace('\\d+', 'X').replace(r'[7-9]', 'X')[:30]
            reasons.append(pattern_name)
    
    # Nigerian bank-specific scams
    nigerian_bank_scams = [
        'gtbank', 'zenithbank', 'firstbank', 'accessbank', 'uba', 
        'fidelitybank', 'unionbank', 'polarisbank', 'ecobank', 'stanbic'
    ]
    
    for bank in nigerian_bank_scams:
        if bank in sms_lower:
            score += 5
            reasons.append(f'{bank}_impersonation')
    
    # Amount detection (common in Nigerian scams)
    amount_patterns = [
        r'₦\s*(\d+[,.]?\d*)',
        r'naira\s*(\d+[,.]?\d*)',
        r'ngn\s*(\d+[,.]?\d*)'
    ]
    
    for pattern in amount_patterns:
        if re.search(pattern, sms_lower):
            score += 3
            reasons.append('monetary_amount')
    
    # =============================================
    # RISK ASSESSMENT & CLASSIFICATION
    # =============================================
    if score >= 25:
        message = '🚨 EXTREME RISK - NIGERIAN ADVANCE FEE SCAM DETECTED!'
        result_type = 'scam'
        detailed_reason = "This shows classic signs of Nigerian '419' advance-fee fraud"
    elif score >= 18:
        message = '🚨 HIGH-RISK SCAM - Likely financial fraud attempt'
        result_type = 'scam'
        detailed_reason = "Multiple scam indicators detected"
    elif score >= 12:
        message = '⚠️ SUSPICIOUS - Potential phishing attempt'
        result_type = 'warning'
        detailed_reason = "Exercise extreme caution"
    elif score >= 8:
        message = '⚠️ CAUTION - Some suspicious elements detected'
        result_type = 'warning'
        detailed_reason = "Verify with official sources"
    else:
        message = '✅ Likely legitimate message'
        result_type = 'safe'
        detailed_reason = "No major scam patterns detected"
    
    # Premium features
    if user['is_premium']:
        premium_features = f'🔍 Premium Analysis: Score {score}/100 - Detected: {", ".join(reasons[:4])} - {detailed_reason}'
    else:
        premium_features = 'Upgrade to Premium for detailed threat analysis and scam pattern breakdown'
    
    return jsonify({
        'message': message,
        'type': result_type,
        'premium_features': premium_features,
        'risk_score': score
    })

@app.route('/api/initiate-payment', methods=['POST'])
def api_initiate_payment():
    data = request.get_json()
    user_id = data.get('user_id')
    plan_type = data.get('plan_type')
    phone_number = data.get('phone_number')
    name = data.get('name')
    
    if not user_id or not plan_type or not phone_number:
        return jsonify({'success': False, 'message': 'Missing required fields'})
    
    if plan_type not in PRICING_PLANS:
        return jsonify({'success': False, 'message': 'Invalid plan type'})
    
    # Create payment record
    payment = PaymentManager.create_payment(user_id, plan_type, phone_number, name)
    
    return jsonify({
        'success': True,
        'payment_id': payment['id'],
        'message': 'Payment initiated successfully'
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
        'user_premium': user['is_premium'] if user else False,
        'premium_until': user.get('premium_until') if user else None
    })

# =============================================
# ADMIN ENDPOINTS
# =============================================

@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    users = UserManager.get_all_users()
    return jsonify(users)

@app.route('/api/admin/payments', methods=['GET'])
def api_admin_payments():
    payments = PaymentManager.get_all_payments()
    return jsonify(payments)

@app.route('/api/admin/verify-payment', methods=['POST'])
def api_admin_verify_payment():
    data = request.get_json()
    payment_id = data.get('payment_id')
    
    payment = PaymentManager.get_payment(payment_id)
    if not payment:
        return jsonify({'success': False, 'message': 'Payment not found'})
    
    # Mark payment as verified
    PaymentManager.update_payment(payment_id, {
        'status': 'verified',
        'verified_at': datetime.now().isoformat()
    })
    
    # Activate premium for user
    user = UserManager.get_user(payment['user_id'])
    if user:
        UserManager.activate_premium(user, payment['plan_type'])
    
    return jsonify({
        'success': True,
        'message': f'Premium activated for user {payment["user_id"]}'
    })

@app.route('/api/admin/activate-premium', methods=['POST'])
def api_admin_activate_premium():
    data = request.get_json()
    user_id = data.get('user_id')
    plan_type = data.get('plan_type', 'weekly')
    
    user = UserManager.get_user(user_id)
    if not user:
        return jsonify({'success': False, 'message': 'User not found'})
    
    # Activate premium
    UserManager.activate_premium(user, plan_type)
    
    return jsonify({
        'success': True,
        'message': f'Premium {plan_type} activated for user {user_id}'
    })

@app.route('/api/admin/verify-user', methods=['POST'])
def api_admin_verify_user():
    data = request.get_json()
    user_id = data.get('user_id')
    
    user = UserManager.get_user(user_id)
    if user:
        UserManager.verify_user_email(user['id'])
        return jsonify({'success': True, 'message': f'User {user_id} verified'})
    return jsonify({'success': False, 'message': 'User not found'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)
else:
    application = app
