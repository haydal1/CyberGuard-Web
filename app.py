from dotenv import load_dotenv
load_dotenv()

import atexit
from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
import re
from datetime import datetime, timedelta
import json
import smtplib
import random
import hashlib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# =============================================
# BUSINESS CONFIGURATION
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

# Get email configuration from environment variables
EMAIL_CONFIG = {
    'sender_email': os.environ.get('SENDER_EMAIL', ''),
    'sender_password': os.environ.get('EMAIL_PASSWORD', ''),
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

# =============================================
# ENHANCED DATABASE MANAGER WITH MONGODB
# =============================================


class Database:
    _client = None
    _db = None
    _sqlite_conn = None
    _in_memory_storage = {
        'users': {},
        'payments': {},
        'sessions': {},
        'otp_storage': {}
    }
    
    @staticmethod
    def get_db():
        if Database._db is None:
            try:
                # Get connection string
                connection_string = os.environ.get('MONGODB_URI')
                if not connection_string:
                    logger.warning("❌ MONGODB_URI not found in environment")
                    # Try alternative environment variable names
                    connection_string = os.environ.get('MONGODB_URL') or os.environ.get('DATABASE_URL')
                    
                if not connection_string:
                    # For local development without MongoDB
                    logger.warning("⚠️ No MongoDB connection string found")
                    
                    # Check if we're in local development mode
                    if os.environ.get('FLASK_DEBUG') == 'True' or os.environ.get('LOCAL_DEV'):
                        logger.info("🖥️ Local development mode - using SQLite fallback")
                        Database._setup_sqlite_fallback()
                        return "sqlite"  # Return a marker instead of None
                    
                    return None
                
                # Mask for logging (security)
                if '@' in connection_string:
                    parts = connection_string.split('@')
                    user_part = parts[0]
                    if ':' in user_part:
                        user_pass = user_part.split(':')
                        masked = user_pass[0] + ':••••••••@' + parts[1]
                        logger.info(f"🔗 Connecting to MongoDB: {masked}")
                
                # Different timeouts for local vs production
                is_local = 'localhost' in connection_string or '127.0.0.1' in connection_string
                timeout = 5000 if is_local else 10000
                
                Database._client = MongoClient(connection_string, 
                                             serverSelectionTimeoutMS=timeout,
                                             maxPoolSize=50,
                                             connectTimeoutMS=timeout)
                
                # Test connection
                Database._client.admin.command('ping')
                
                # Extract database name
                db_name = 'atlas-purple-book'  # Default for Vercel
                
                # Try to extract from connection string
                if 'mongodb.net/' in connection_string:
                    # MongoDB Atlas format
                    parts = connection_string.split('.mongodb.net/')
                    if len(parts) > 1:
                        db_part = parts[1]
                        if '?' in db_part:
                            possible_name = db_part.split('?')[0]
                            if possible_name and possible_name.strip():
                                db_name = possible_name
                
                logger.info(f"📦 Using database: {db_name}")
                Database._db = Database._client[db_name]
                logger.info(f"✅ Connected to MongoDB database: {db_name}")
                
                # Ensure collections exist
                collections = ['users', 'payments', 'sessions', 'otp_storage']
                existing = Database._db.list_collection_names()
                
                for collection_name in collections:
                    if collection_name not in existing:
                        Database._db.create_collection(collection_name)
                        logger.info(f"📁 Created collection: {collection_name}")
                
                logger.info(f"📊 Collections: {Database._db.list_collection_names()}")
                return Database._db
                
            except Exception as e:
                logger.error(f"❌ MongoDB connection failed: {e}")
                
                # Fallback to SQLite for local development
                if os.environ.get('FLASK_DEBUG') == 'True':
                    logger.info("🔄 Falling back to SQLite for local development")
                    Database._setup_sqlite_fallback()
                    return "sqlite"  # Return a marker instead of None
                
                return None
        return Database._db
    
    @staticmethod
    def _setup_sqlite_fallback():
        """Setup SQLite as a fallback for local development"""
        try:
            import sqlite3
            from contextlib import closing
            
            logger.info("💾 Setting up SQLite database...")
            
            # Create an in-memory SQLite connection
            Database._sqlite_conn = sqlite3.connect(':memory:', check_same_thread=False)
            Database._sqlite_conn.row_factory = sqlite3.Row
            
            # Create tables
            with closing(Database._sqlite_conn.cursor()) as cur:
                # Users table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE,
                        password_hash TEXT,
                        phone_number TEXT,
                        name TEXT,
                        is_verified BOOLEAN DEFAULT 0,
                        is_premium BOOLEAN DEFAULT 0,
                        premium_until TEXT,
                        premium_plan TEXT,
                        checks_today INTEGER DEFAULT 0,
                        last_check_date TEXT,
                        total_checks INTEGER DEFAULT 0,
                        payment_pending BOOLEAN DEFAULT 0,
                        created_at TEXT,
                        last_login TEXT,
                        reset_tokens TEXT DEFAULT '[]'
                    )
                ''')
                
                # Payments table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS payments (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        plan_type TEXT,
                        phone_number TEXT,
                        name TEXT,
                        amount INTEGER,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT,
                        verified_at TEXT
                    )
                ''')
                
                # Sessions table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_token TEXT PRIMARY KEY,
                        user_id TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        created_at TEXT,
                        expires_at TEXT,
                        last_accessed TEXT
                    )
                ''')
                
                # OTP storage table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS otp_storage (
                        email TEXT PRIMARY KEY,
                        otp_code TEXT,
                        created_at TEXT,
                        expires_at TEXT,
                        verified BOOLEAN DEFAULT 0
                    )
                ''')
                
                Database._sqlite_conn.commit()
            
            logger.info("✅ SQLite database setup complete")
            
        except Exception as e:
            logger.error(f"❌ SQLite setup failed: {e}")
            return None
    
    @staticmethod
    def is_sqlite_mode():
        """Check if we're using SQLite fallback"""
        return Database._sqlite_conn is not None
    
    @staticmethod
    def get_collection(collection_name):
        db = Database.get_db()
        
        # If using SQLite, return None (we'll handle SQLite separately)
        if db == "sqlite" or Database.is_sqlite_mode():
            return None
        
        # If MongoDB is connected, return the collection
        if db is not None and db != "sqlite" and hasattr(db, '__getitem__'):
            try:
                return db[collection_name]
            except Exception as e:
                logger.warning(f"⚠️ Could not get collection {collection_name}: {e}")
        
        # In-memory fallback
        logger.warning(f"⚠️ Using in-memory fallback for {collection_name}")
        return Database._in_memory_storage.get(collection_name, {})
    
    # Update all load/save methods to handle SQLite
    @staticmethod
    def load_users():
        # Check if using SQLite
        if Database.is_sqlite_mode():
            try:
                users = {}
                with Database._sqlite_conn:
                    cur = Database._sqlite_conn.cursor()
                    cur.execute("SELECT * FROM users")
                    rows = cur.fetchall()
                    for row in rows:
                        user_dict = dict(row)
                        users[user_dict['id']] = user_dict
                logger.info(f"📥 Loaded {len(users)} users from SQLite")
                return users
            except Exception as e:
                logger.error(f"Error loading users from SQLite: {e}")
                return {}
        
        # Original MongoDB code
        try:
            collection = Database.get_collection('users')
            if isinstance(collection, dict):
                # In-memory fallback
                return collection
            
            users = {}
            for user in collection.find():
                user_dict = {k: v for k, v in user.items() if k != '_id'}
                # Convert MongoDB types to Python types
                if 'created_at' in user_dict and isinstance(user_dict['created_at'], datetime):
                    user_dict['created_at'] = user_dict['created_at'].isoformat()
                if 'last_login' in user_dict and isinstance(user_dict['last_login'], datetime):
                    user_dict['last_login'] = user_dict['last_login'].isoformat()
                if 'premium_until' in user_dict and isinstance(user_dict['premium_until'], datetime):
                    user_dict['premium_until'] = user_dict['premium_until'].isoformat()
                if 'last_check_date' in user_dict and isinstance(user_dict['last_check_date'], datetime):
                    user_dict['last_check_date'] = user_dict['last_check_date'].isoformat()
                if 'reset_tokens' in user_dict and isinstance(user_dict['reset_tokens'], list):
                    user_dict['reset_tokens'] = json.dumps(user_dict['reset_tokens'])
                
                users[user_dict['id']] = user_dict
            
            logger.info(f"📥 Loaded {len(users)} users from MongoDB")
            return users
            
        except Exception as e:
            logger.error(f"Error loading users from MongoDB: {e}")
            return getattr(Database, '_users_cache', {})
    
    @staticmethod
    def save_users(users):
        # Check if using SQLite
        if Database.is_sqlite_mode():
            try:
                with Database._sqlite_conn:
                    cur = Database._sqlite_conn.cursor()
                    # Clear table first
                    cur.execute("DELETE FROM users")
                    # Insert all users
                    for user_id, user_data in users.items():
                        placeholders = ', '.join(['?'] * (len(user_data) + 1))
                        columns = ', '.join(['id'] + list(user_data.keys()))
                        values = [user_id] + list(user_data.values())
                        cur.execute(f"INSERT INTO users ({columns}) VALUES ({placeholders})", values)
                logger.info(f"💾 Saved {len(users)} users to SQLite")
                return True
            except Exception as e:
                logger.error(f"Error saving users to SQLite: {e}")
                return False
        
        # Original MongoDB code
        try:
            collection = Database.get_collection('users')
            if isinstance(collection, dict):
                # In-memory fallback
                collection.clear()
                collection.update(users)
                logger.warning(f"⚠️ Saved {len(users)} users to in-memory storage")
                return True
            
            users_list = []
            for user_id, user_data in users.items():
                # Ensure all required fields exist
                user_data['id'] = user_id
                user_data['_id'] = user_id  # Use user_id as _id for easier updates
                
                # Convert string dates back to datetime
                if 'created_at' in user_data and isinstance(user_data['created_at'], str):
                    user_data['created_at'] = datetime.fromisoformat(user_data['created_at'].replace('Z', '+00:00'))
                if 'last_login' in user_data and isinstance(user_data['last_login'], str):
                    user_data['last_login'] = datetime.fromisoformat(user_data['last_login'].replace('Z', '+00:00'))
                if 'premium_until' in user_data and isinstance(user_data['premium_until'], str):
                    user_data['premium_until'] = datetime.fromisoformat(user_data['premium_until'].replace('Z', '+00:00'))
                if 'last_check_date' in user_data and isinstance(user_data['last_check_date'], str):
                    user_data['last_check_date'] = datetime.fromisoformat(user_data['last_check_date'].replace('Z', '+00:00'))
                if 'reset_tokens' in user_data and isinstance(user_data['reset_tokens'], str):
                    user_data['reset_tokens'] = json.loads(user_data['reset_tokens'])
                
                users_list.append(user_data)
            
            if users_list:
                # Update or insert each user
                for user in users_list:
                    collection.replace_one({'_id': user['_id']}, user, upsert=True)
            
            logger.info(f"💾 Saved/Updated {len(users_list)} users to MongoDB")
            return True
            
        except Exception as e:
            logger.error(f"Error saving users to MongoDB: {e}")
            import traceback
            logger.error(f"Save users traceback: {traceback.format_exc()}")
            return False
    
    @staticmethod
    def load_payments():
        try:
            collection = Database.get_collection('payments')
            if isinstance(collection, dict):
                return collection
            
            payments = {}
            for payment in collection.find():
                payment_dict = {k: v for k, v in payment.items() if k != '_id'}
                # Convert datetime to string
                for date_field in ['created_at', 'verified_at']:
                    if date_field in payment_dict and isinstance(payment_dict[date_field], datetime):
                        payment_dict[date_field] = payment_dict[date_field].isoformat()
                
                payments[payment_dict['id']] = payment_dict
            
            return payments
            
        except Exception as e:
            logger.error(f"Error loading payments from MongoDB: {e}")
            return getattr(Database, '_payments_cache', {})
    
    @staticmethod
    def save_payments(payments):
        try:
            collection = Database.get_collection('payments')
            if isinstance(collection, dict):
                collection.clear()
                collection.update(payments)
                return True
            
            payments_list = []
            for payment_id, payment_data in payments.items():
                payment_data['id'] = payment_id
                payment_data['_id'] = payment_id
                
                # Convert string dates back to datetime
                for date_field in ['created_at', 'verified_at']:
                    if date_field in payment_data and isinstance(payment_data[date_field], str):
                        payment_data[date_field] = datetime.fromisoformat(payment_data[date_field].replace('Z', '+00:00'))
                
                payments_list.append(payment_data)
            
            if payments_list:
                for payment in payments_list:
                    collection.replace_one({'_id': payment['_id']}, payment, upsert=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving payments to MongoDB: {e}")
            return False
    
    @staticmethod
    def load_sessions():
        try:
            collection = Database.get_collection('sessions')
            if isinstance(collection, dict):
                return collection
            
            sessions = {}
            for session in collection.find():
                session_dict = {k: v for k, v in session.items() if k != '_id'}
                # Convert datetime to string
                for date_field in ['created_at', 'expires_at', 'last_accessed']:
                    if date_field in session_dict and isinstance(session_dict[date_field], datetime):
                        session_dict[date_field] = session_dict[date_field].isoformat()
                
                sessions[session_dict.get('session_token')] = session_dict
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error loading sessions from MongoDB: {e}")
            return getattr(Database, '_sessions_cache', {})
    
    @staticmethod
    def save_sessions(sessions):
        try:
            collection = Database.get_collection('sessions')
            if isinstance(collection, dict):
                collection.clear()
                collection.update(sessions)
                return True
            
            sessions_list = []
            for session_token, session_data in sessions.items():
                session_data['session_token'] = session_token
                session_data['_id'] = session_token
                
                # Convert string dates back to datetime
                for date_field in ['created_at', 'expires_at', 'last_accessed']:
                    if date_field in session_data and isinstance(session_data[date_field], str):
                        session_data[date_field] = datetime.fromisoformat(session_data[date_field].replace('Z', '+00:00'))
                
                sessions_list.append(session_data)
            
            if sessions_list:
                for session in sessions_list:
                    collection.replace_one({'_id': session['_id']}, session, upsert=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving sessions to MongoDB: {e}")
            return False
    
    @staticmethod
    def load_otp_storage():
        try:
            collection = Database.get_collection('otp_storage')
            if isinstance(collection, dict):
                return collection
            
            otp_storage = {}
            for otp in collection.find():
                otp_dict = {k: v for k, v in otp.items() if k != '_id'}
                # Convert datetime to string
                for date_field in ['created_at', 'expires_at']:
                    if date_field in otp_dict and isinstance(otp_dict[date_field], datetime):
                        otp_dict[date_field] = otp_dict[date_field].isoformat()
                
                otp_storage[otp_dict.get('email')] = otp_dict
            
            return otp_storage
            
        except Exception as e:
            logger.error(f"Error loading OTP storage from MongoDB: {e}")
            return getattr(Database, '_otp_cache', {})
    
    @staticmethod
    def save_otp_storage(otp_storage):
        try:
            collection = Database.get_collection('otp_storage')
            if isinstance(collection, dict):
                collection.clear()
                collection.update(otp_storage)
                return True
            
            otp_list = []
            for email, otp_data in otp_storage.items():
                otp_data['email'] = email
                otp_data['_id'] = email
                
                # Convert string dates back to datetime
                for date_field in ['created_at', 'expires_at']:
                    if date_field in otp_data and isinstance(otp_data[date_field], str):
                        otp_data[date_field] = datetime.fromisoformat(otp_data[date_field].replace('Z', '+00:00'))
                
                otp_list.append(otp_data)
            
            if otp_list:
                for otp in otp_list:
                    collection.replace_one({'_id': otp['_id']}, otp, upsert=True)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving OTP storage to MongoDB: {e}")
            return False

# Add cleanup function for Vercel
def close_mongo_connection():
    """Close MongoDB connection when app stops (important for Vercel)"""
    if Database._client:
        Database._client.close()
        logger.info("🔌 MongoDB connection closed")
        Database._client = None
        Database._db = None

# Register cleanup
atexit.register(close_mongo_connection)

# =============================================
# ENHANCED EMAIL SERVICE
# =============================================

class EmailService:
    @staticmethod
    def send_otp_email(recipient_email, otp_code):
        """Send OTP code to user's email"""
        try:
            # Check if email config is valid
            sender_email = EMAIL_CONFIG['sender_email']
            sender_password = EMAIL_CONFIG['sender_password']
            
            # Debug logging
            logger.info(f"📧 Email Config Check:")
            logger.info(f"   Sender Email: {'SET' if sender_email else 'MISSING'}")
            logger.info(f"   Sender Password: {'SET' if sender_password else 'MISSING'}")
            
            if not sender_email or not sender_password:
                logger.error("❌ Email configuration missing")
                logger.error(f"   Email: {sender_email}")
                logger.error(f"   Password: {'Set' if sender_password else 'Missing'}")
                return False
            
            logger.info(f"📧 Sending OTP to {recipient_email}")
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = "CyberGuard NG - Email Verification OTP"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #0056b3;">🛡️ CyberGuard NG Email Verification</h2>
                <p>Your OTP verification code is:</p>
                <h1 style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 32px; letter-spacing: 5px; border-radius: 8px;">
                    {otp_code}
                </h1>
                <p>This code will expire in 10 minutes.</p>
                <p><em>If you didn't request this code, please ignore this email.</em></p>
                <hr>
                <p>Best regards,<br><strong>CyberGuard NG Team</strong></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            # Connect to SMTP server
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ OTP email sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Email error: {str(e)}")
            return False

    @staticmethod
    def send_password_reset_email(recipient_email, reset_token):
        """Send password reset email"""
        try:
            # Check if email config is valid
            sender_email = EMAIL_CONFIG['sender_email']
            sender_password = EMAIL_CONFIG['sender_password']
            
            if not sender_email or not sender_password:
                logger.error("❌ Email configuration missing")
                return False
            
            reset_link = f"https://cyber-guard-web.vercel.app/#reset-password?token={reset_token}"
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = "CyberGuard NG - Password Reset Request"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #0056b3;">🛡️ CyberGuard NG Password Reset</h2>
                <p>You requested to reset your password. Click the link below to create a new password:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        Reset Your Password
                    </a>
                </p>
                <p>This link will expire in 1 hour.</p>
                <p><em>If you didn't request this reset, please ignore this email.</em></p>
                <hr>
                <p>Best regards,<br><strong>CyberGuard NG Team</strong></p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"✅ Password reset email sent to {recipient_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Password reset email error: {e}")
            return False

# =============================================
# ENHANCED AUTHENTICATION MANAGER
# =============================================

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
    def generate_reset_token():
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_session(user_id):
        sessions = Database.load_sessions()
        session_token = AuthManager.generate_session_token()
        
        session_data = {
            'session_token': session_token,
            'user_id': user_id,
            'ip_address': request.remote_addr,
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
            
            if datetime.now() > expires_at:
                del sessions[session_token]
                Database.save_sessions(sessions)
                return None
            
            if session_data.get('ip_address') != request.remote_addr:
                del sessions[session_token]
                Database.save_sessions(sessions)
                return None
            
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

# =============================================
# ENHANCED USER MANAGER
# =============================================

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
            'last_login': datetime.now().isoformat(),
            'reset_tokens': []  # Store reset tokens for security
        }
        
        users[user_id] = user_data
        if Database.save_users(users):
            return user_data, None
        return None, "Failed to save user"

    @staticmethod
    def authenticate_user(email, password):
        users = Database.load_users()
        for user in users.values():
            if user.get('email') == email and AuthManager.verify_password(password, user['password_hash']):
                user['last_login'] = datetime.now().isoformat()
                users[user['id']] = user
                Database.save_users(users)
                return user
        return None

    @staticmethod
    def get_user(user_id):
        users = Database.load_users()
        if user_id in users:
            users[user_id]['last_active'] = datetime.now().isoformat()
            Database.save_users(users)
            return users[user_id]
        return None

    @staticmethod
    def get_user_by_email(email):
        users = Database.load_users()
        for user in users.values():
            if user.get('email') == email:
                return user
        return None

    @staticmethod
    def verify_user_email(user_id):
        users = Database.load_users()
        if user_id in users:
            users[user_id]['is_verified'] = True
            return Database.save_users(users)
        return False

    @staticmethod
    def save_user(user):
        users = Database.load_users()
        users[user['id']] = user
        return Database.save_users(users)

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

    @staticmethod
    def create_password_reset_token(email):
        user = UserManager.get_user_by_email(email)
        if not user:
            return None
        
        reset_token = AuthManager.generate_reset_token()
        token_data = {
            'token': reset_token,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
            'used': False
        }
        
        if 'reset_tokens' not in user:
            user['reset_tokens'] = []
        
        # Remove expired tokens
        user['reset_tokens'] = [
            token for token in user.get('reset_tokens', [])
            if datetime.now() < datetime.fromisoformat(token['expires_at']) and not token['used']
        ]
        
        user['reset_tokens'].append(token_data)
        UserManager.save_user(user)
        
        return reset_token

    @staticmethod
    def validate_reset_token(email, token):
        user = UserManager.get_user_by_email(email)
        if not user or 'reset_tokens' not in user:
            return False
        
        for token_data in user['reset_tokens']:
            if (token_data['token'] == token and 
                not token_data['used'] and 
                datetime.now() < datetime.fromisoformat(token_data['expires_at'])):
                return True
        
        return False

    @staticmethod
    def use_reset_token(email, token):
        user = UserManager.get_user_by_email(email)
        if not user:
            return False
        
        for token_data in user['reset_tokens']:
            if token_data['token'] == token:
                token_data['used'] = True
                token_data['used_at'] = datetime.now().isoformat()
                return UserManager.save_user(user)
        
        return False

    @staticmethod
    def update_password(email, new_password):
        user = UserManager.get_user_by_email(email)
        if not user:
            return False
        
        user['password_hash'] = AuthManager.hash_password(new_password)
        # Clear all reset tokens after password change
        user['reset_tokens'] = []
        return UserManager.save_user(user)

# =============================================
# OTP MANAGER
# =============================================

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

# =============================================
# PAYMENT MANAGER
# =============================================

class PaymentManager:
    @staticmethod
    def create_payment(user_id, plan_type, phone_number, name=None):
        payments = Database.load_payments()
        payment_id = f"pay_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}"
        
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
        if Database.save_payments(payments):
            # Update user to show payment pending
            user = UserManager.get_user(user_id)
            if user:
                user['payment_pending'] = True
                if name and not user.get('name'):
                    user['name'] = name
                UserManager.save_user(user)
            
            return payment
        return None
    
    @staticmethod
    def get_payment(payment_id):
        payments = Database.load_payments()
        return payments.get(payment_id)
    
    @staticmethod
    def update_payment(payment_id, updates):
        payments = Database.load_payments()
        if payment_id in payments:
            payments[payment_id].update(updates)
            return Database.save_payments(payments)
        return False
    
    @staticmethod
    def get_all_payments():
        return Database.load_payments()

# =============================================
# SIMPLE SCANNER CLASS
# =============================================

class SimpleScanner:
    def __init__(self):
        self.known_scam_domains = {
            'tcnnationalizeuze.site', 'gtbank-verify.tk', 
            'nigerianlottery.com', 'zenithbank-update.xyz',
            'profitize.site', 'moneytized.online'
        }
        
        self.legitimate_domains = {
            'zenithbank.com', 'facebook.com', 'google.com',
            'gtbank.com', 'firstbanknigeria.com', 'accessbankplc.com'
        }

    def scan_url(self, url):
        """Simple URL scanner without complex fraud detection"""
        try:
            # Normalize URL
            normalized_url = url.lower().strip()
            if not normalized_url.startswith(('http://', 'https://')):
                normalized_url = 'http://' + normalized_url
            
            # Extract domain
            domain = self.extract_domain(normalized_url)
            
            # Check against known lists
            if domain in self.known_scam_domains:
                return {
                    'message': '🚨 HIGH RISK - Known scam domain',
                    'type': 'scam'
                }
            
            if domain in self.legitimate_domains:
                return {
                    'message': '✅ SAFE - Legitimate website',
                    'type': 'safe'
                }
            
            # Basic pattern checks
            suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.xyz', '.top', '.club', '.site', '.online']
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                return {
                    'message': '⚠️ WARNING - Suspicious domain characteristics',
                    'type': 'warning'
                }
            
            return {
                'message': '✅ Likely safe - No major issues detected',
                'type': 'safe'
            }
                
        except Exception as e:
            logger.error(f"Error scanning URL: {e}")
            return {
                'message': '❌ Scan failed - Please try again',
                'type': 'error'
            }

    def extract_domain(self, url):
        """Extract domain from URL"""
        try:
            # Remove protocol and path
            domain = url.split('//')[-1].split('/')[0]
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url

# Initialize scanner
scanner = SimpleScanner()

# =============================================
# FLASK ROUTES
# =============================================

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
            position: relative;
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
            flex-wrap: wrap;
        }
        .tab {
            flex: 1;
            padding: 15px;
            text-align: center;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
            min-width: 120px;
        }
        .tab:hover {
            background: #e9ecef;
        }
        .tab.active {
            background: white;
            border-bottom: 3px solid #007bff;
            font-weight: bold;
        }
        .tab-content {
            display: none;
            padding: 30px;
            min-height: 400px;
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
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
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
        .error { background: #f8d7da; color: #721c24; border: 2px solid #f5c6cb; }
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
            flex-wrap: wrap;
        }
        .pricing-card {
            flex: 1;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
            min-width: 250px;
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
            display: none;
        }
        .forgot-password {
            text-align: center;
            margin-top: 15px;
        }
        .forgot-password a {
            color: #007bff;
            text-decoration: none;
        }
        .forgot-password a:hover {
            text-decoration: underline;
        }
        
        @media (max-width: 768px) {
            .pricing-cards { flex-direction: column; }
            .tabs { flex-direction: column; }
            .user-menu { 
                position: relative; 
                top: 0; 
                right: 0; 
                margin: 10px; 
                text-align: center;
            }
            .tab { min-width: 100%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ CyberGuard NG <span class="premium-badge">PREMIUM</span></h1>
            <p>Advanced Nigerian Fraud Protection with Premium Features</p>
            
            <div id="userMenu" class="user-menu">
                <span id="userGreeting"></span>
                <button class="btn" onclick="logout()" style="padding: 5px 10px; margin-left: 10px; width: auto;">Logout</button>
            </div>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('scanner', event)">Security Scanner</button>
            <button class="tab" onclick="switchTab('register', event)">Register</button>
            <button class="tab" onclick="switchTab('verify', event)">Verify Email</button>
            <button class="tab" onclick="switchTab('login', event)">Login</button>
            <button class="tab" onclick="switchTab('premium', event)">Go Premium</button>
            <button class="tab" onclick="switchTab('account', event)">My Account</button>
            <button class="tab" onclick="switchTab('admin', event)">Admin</button>
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
                <h2>🔍 Security Scanner</h2>
                <p>Enter any Nigerian phone number, website URL, or business name to check for fraud risks</p>
                
                <div class="section">
                    <h3>Check USSD Code Safety</h3>
                    <div class="input-group">
                        <input type="text" id="ussdInput" placeholder="Enter USSD code e.g. *901#" value="*901#">
                    </div>
                    <button class="btn" onclick="checkUSSD()">🔍 Check USSD Safety</button>
                </div>
                
                <div class="section">
                    <h3>Scan SMS for Scams</h3>
                    <div class="input-group">
                        <textarea id="smsInput" placeholder="Paste suspicious SMS message here...">Congratulations! You have won 5,000,000 Naira! Call 08012345678 to claim your prize.</textarea>
                    </div>
                    <button class="btn btn-danger" onclick="checkSMS()">📱 Scan SMS for Fraud</button>
                </div>
            </div>
            
            <div id="scannerResult" class="result">Ready to protect you from Nigerian fraud...</div>
        </div>
        
        <!-- REGISTER TAB -->
        <div id="register-content" class="tab-content">
            <h2>Register for CyberGuard NG</h2>
            <p>Create your account to start protecting yourself from fraud</p>

            <div class="registration-section">
                <form onsubmit="registerUser(); return false">
                    <div class="input-group">
                        <input type="text" id="userName" placeholder="Your Full Name" autocomplete="name">
                    </div>
                    <div class="input-group">
                        <input type="email" id="userEmail" placeholder="Your Email Address (Required)" required autocomplete="email">
                    </div>
                    <div class="input-group">
                        <input type="password" id="userPassword" placeholder="Password (Minimum 6 characters)" required autocomplete="new-password">
                    </div>
                    <div class="input-group">
                        <input type="password" id="userConfirmPassword" placeholder="Confirm Password" required autocomplete="new-password">
                    </div>
                    <div class="input-group">
                        <input type="text" id="userPhone" placeholder="Your WhatsApp Number (Required)" required autocomplete="tel">
                    </div>
                    <button type="submit" class="btn btn-premium">Create Account & Send OTP</button>
                </form>
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
                    <button class="btn" onclick="switchTab('scanner', event)">Start Scanning Now</button>
                </div>
            </div>
        </div>
        
        <!-- VERIFY EMAIL TAB -->
        <div id="verify-content" class="tab-content">
            <h2>Verify Your Email</h2>
            <p>Enter your email to receive a new verification code</p>

            <div class="registration-section">
                <form onsubmit="sendVerificationOTP(); return false">
                    <div class="input-group">
                        <input type="email" id="verifyEmail" placeholder="Enter your registered email" required autocomplete="email">
                    </div>
                    <button type="submit" class="btn btn-premium">Send New OTP Code</button>
                </form>
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
                    <button class="btn" onclick="switchTab('login', event)">Login Now</button>
                </div>
            </div>
        </div>
        
        <!-- LOGIN TAB -->
        <div id="login-content" class="tab-content">
            <h2>Login to Your Account</h2>
            <p>Access your CyberGuard NG account</p>

            <div class="login-section">
                <form onsubmit="loginUser(); return false">
                    <div class="input-group">
                        <input type="email" id="loginEmail" placeholder="Your Email Address" autocomplete="email" required>
                    </div>
                    <div class="input-group">
                        <input type="password" id="loginPassword" placeholder="Your Password" autocomplete="current-password" required>
                    </div>
                    <button type="submit" class="btn btn-premium">Login to Account</button>
                </form>
                
                <div class="forgot-password">
                    <a href="javascript:void(0)" onclick="showForgotPassword()">Forgot Password?</a>
                </div>
                
                <p style="margin-top: 15px; text-align: center;">
                    Don't have an account? <a href="javascript:void(0)" onclick="switchTab('register', event)">Register here</a>
                </p>
            </div>

            <!-- Forgot Password Section -->
            <div id="forgotPasswordSection" class="registration-section" style="display: none;">
                <h3>🔐 Reset Your Password</h3>
                <form onsubmit="forgotPassword(); return false">
                    <div class="input-group">
                        <input type="email" id="forgotPasswordEmail" placeholder="Enter your registered email" required autocomplete="email">
                    </div>
                    <button type="submit" class="btn btn-warning">Send Reset Link</button>
                </form>
                <div class="forgot-password">
                    <a href="javascript:void(0)" onclick="hideForgotPassword()">Back to Login</a>
                </div>
            </div>

            <!-- Reset Password Section -->
            <div id="resetPasswordSection" class="registration-section" style="display: none;">
                <h3>🔐 Create New Password</h3>
                <form onsubmit="resetPassword(); return false">
                    <div class="input-group">
                        <input type="hidden" id="resetToken">
                        <input type="password" id="newPassword" placeholder="New Password (Minimum 6 characters)" required autocomplete="new-password">
                    </div>
                    <div class="input-group">
                        <input type="password" id="confirmPassword" placeholder="Confirm New Password" required autocomplete="new-password">
                    </div>
                    <button type="submit" class="btn btn-premium">Reset Password</button>
                </form>
            </div>
        </div>
        
        <!-- PREMIUM TAB -->
        <div id="premium-content" class="tab-content">
            <h2>🚀 Upgrade to CyberGuard Premium</h2>
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
                            <li>✓ Advanced detection</li>
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
                        <p><strong>Bank:</strong> ''' + YOUR_BANK_DETAILS['bank_name'] + '''</p>
                        <p><strong>Account Number:</strong> ''' + YOUR_BANK_DETAILS['account_number'] + '''</p>
                        <p><strong>Account Name:</strong> ''' + YOUR_BANK_DETAILS['account_name'] + '''</p>
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
                                <li>WhatsApp screenshot to: <strong>''' + YOUR_CONTACT['whatsapp_number'] + '''</strong></li>
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
                    <button class="btn btn-premium" onclick="switchTab('premium', event)">Upgrade to Premium</button>
                </div>
            </div>
        </div>
        
        <!-- ADMIN TAB -->
        <div id="admin-content" class="tab-content">
            <h2>Admin Panel</h2>
            <p>Restricted access - authorized personnel only</p>

            <div class="input-group">
                <form onsubmit="loginAdmin(); return false">
                    <input type="password" id="adminPassword" placeholder="Enter Admin Password" autocomplete="current-password" required>
                    <button type="submit" class="btn btn-info">Access Admin Panel</button>
                </form>
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
        
        // Check for reset token in URL
        document.addEventListener('DOMContentLoaded', function() {
            checkExistingSession();
            checkResetToken();
        });
        
        function checkResetToken() {
            const urlParams = new URLSearchParams(window.location.hash.substring(1));
            const resetToken = urlParams.get('token');
            if (resetToken) {
                document.getElementById('resetToken').value = resetToken;
                switchTab('login');
                document.getElementById('forgotPasswordSection').style.display = 'none';
                document.getElementById('resetPasswordSection').style.display = 'block';
            }
        }
        
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
                console.error('Session validation error:', error);
                showNotLoggedInUI();
            }
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
        
        function switchTab(tabName, event = null) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab content
            document.getElementById(tabName + '-content').classList.add('active');
            
            // Add active class to clicked tab
            if (event) {
                event.currentTarget.classList.add('active');
            } else {
                // Find and activate the tab button
                const tabs = document.querySelectorAll('.tab');
                for (let tab of tabs) {
                    if (tab.onclick && tab.onclick.toString().includes(tabName)) {
                        tab.classList.add('active');
                        break;
                    }
                }
            }
            
            // Special handling for account tab
            if (tabName === 'account' && currentUser) {
                updateAccountInfo();
            }
            
            // Reset forgot password section when switching to login
            if (tabName === 'login') {
                hideForgotPassword();
            }
        }
        
        function showForgotPassword() {
            document.getElementById('forgotPasswordSection').style.display = 'block';
        }
        
        function hideForgotPassword() {
            document.getElementById('forgotPasswordSection').style.display = 'none';
            document.getElementById('resetPasswordSection').style.display = 'none';
        }
        
        async function forgotPassword() {
            const email = document.getElementById('forgotPasswordEmail').value;
            
            if (!email) {
                alert('Please enter your email address');
                return;
            }
            
            try {
                const response = await fetch('/api/forgot-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: email })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Password reset link sent to your email! Check your inbox.');
                    hideForgotPassword();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }
        
        async function resetPassword() {
            const token = document.getElementById('resetToken').value;
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            
            if (!token) {
                alert('Invalid reset token');
                return;
            }
            
            if (!newPassword || !confirmPassword) {
                alert('Please fill in all fields');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                alert('Passwords do not match');
                return;
            }
            
            if (newPassword.length < 6) {
                alert('Password must be at least 6 characters long');
                return;
            }
            
            try {
                const response = await fetch('/api/reset-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        token: token,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ Password reset successfully! You can now login with your new password.');
                    hideForgotPassword();
                    // Clear the form
                    document.getElementById('newPassword').value = '';
                    document.getElementById('confirmPassword').value = '';
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Network error. Please try again.');
            }
        }

        // =============================================
        // SCANNER FUNCTIONS
        // =============================================

        async function checkUSSD() {
            if (!currentUser) {
                alert('Please login first');
                switchTab('login');
                return;
            }
            
            const code = document.getElementById('ussdInput').value;
            if (!code) {
                showResult({
                    message: '❌ Please enter a USSD code to check',
                    type: 'warning'
                });
                return;
            }
            
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
                
                if (result.success === false) {
                    showResult({
                        message: '❌ ' + result.message,
                        type: 'warning'
                    });
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
            if (!sms) {
                showResult({
                    message: '❌ Please enter an SMS message to scan',
                    type: 'warning'
                });
                return;
            }
            
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
                
                if (result.success === false) {
                    showResult({
                        message: '❌ ' + result.message,
                        type: 'warning'
                    });
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
            const result = document.getElementById('scannerResult');
            
            if (result) {
                result.textContent = data.message;
                result.className = 'result ' + (data.type || 'warning');
                result.style.display = 'block';
                
                if (data.limit_reached) {
                    setTimeout(() => switchTab('premium'), 2000);
                }
            } else {
                console.error('Result element not found');
            }
        }

        // =============================================
        // USER REGISTRATION & AUTHENTICATION
        // =============================================

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
            
            // Show loading state
            const loginBtn = event.target;
            const originalText = loginBtn.textContent;
            loginBtn.textContent = 'Logging in...';
            loginBtn.disabled = true;
            
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
                
                // Reset button
                loginBtn.textContent = originalText;
                loginBtn.disabled = false;
                
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
                        document.getElementById('userEmail').readOnly = true;
                        document.getElementById('otpVerificationSection').style.display = 'block';
                        
                        document.getElementById('otpVerificationSection').scrollIntoView({ 
                            behavior: 'smooth' 
                        });
                        
                    } else {
                        // Regular login error
                        showResult({
                            message: '❌ ' + result.message,
                            type: 'warning'
                        });
                    }
                }
            } catch (error) {
                // Reset button on error
                loginBtn.textContent = originalText;
                loginBtn.disabled = false;
                
                showResult({
                    message: '❌ Network error. Please check your connection and try again.',
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
                if (data.success) {
                    updateUI(data);
                }
            } catch (error) {
                console.log('Error loading user stats');
            }
        }

        function updateUI(stats) {
            if (!currentUser) return;
            
            const isPremium = stats.is_premium;
            const maxChecks = isPremium ? '∞' : '5';
            
            // Update scanner stats
            document.getElementById('checksCount').textContent = stats.checks_today;
            document.getElementById('maxChecks').textContent = maxChecks;
            document.getElementById('accountType').textContent = isPremium ? 'Premium 🏆' : 'Free';
            
            // Update account info
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

        // =============================================
        // PREMIUM & PAYMENT FUNCTIONS
        // =============================================

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
                'weekly': { price: 1000, name: 'Weekly Premium (7 days)' },
                'monthly': { price: 3000, name: 'Monthly Premium (30 days)' }
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

        // =============================================
        // ADMIN FUNCTIONS
        // =============================================

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
# SCANNER API ENDPOINTS
# =============================================

@app.route('/api/check-ussd', methods=['POST'])
def api_check_ussd():
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = UserManager.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Enforce email verification
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
        
        # USSD fraud detection logic
        safe_bank_codes = [
            '*901#', '*894#', '*737#', '*919#', '*822#', '*533#', 
            '*322#', '*326#', '*779#', '*989#', '*123#', '*500#',
            '*955#', '*833#', '*706#', '*909#', '*966#', '*482#'
        ]
        
        scam_indicators = {
            'password': 10, 'pin': 10, 'bvn': 15, 'winner': 12, 'won': 12,
            'prize': 12, 'lottery': 12, 'claim': 10, 'verification': 8
        }
        
        risk_score = 0
        detected_patterns = []
        
        code_lower = code.lower()
        
        # Check against safe codes
        if code in safe_bank_codes:
            message = '✅ SAFE - Verified Nigerian bank USSD code'
            result_type = 'safe'
        else:
            # Check for scam indicators
            for indicator, points in scam_indicators.items():
                if indicator in code_lower:
                    risk_score += points
                    detected_patterns.append(indicator)
            
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
        
        return jsonify({
            'success': True,
            'message': message,
            'type': result_type
        })
    except Exception as e:
        logger.error(f"USSD check error: {e}")
        return jsonify({'success': False, 'message': 'Server error during USSD check'})

@app.route('/api/check-sms', methods=['POST'])
def api_check_sms():
    try:
        data = request.get_json()
        sms = data.get('sms', '').strip()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
        user = UserManager.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Enforce email verification
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
        
        # SMS fraud detection logic
        sms_lower = sms.lower()
        score = 0
        reasons = []
        
        high_risk_patterns = {
            r'won\s*\d+[,.]?\d*\s*(million|thousand|billion)': 15,
            r'congratulation(s)?!*\s*you\s+(won|have|are)': 12,
            r'prize\s*(money|award|winner)': 10,
            r'lottery|jackpot|raffle': 10,
            r'claim\s*(your|this|now)': 8,
            r'free\s*(money|airtime|data|gift)': 8,
            r'account\s*verification': 7,
            r'password\s*reset': 7,
            r'bvn\s*(verification|update)': 15,
            r'atm\s*card\s*(details|pin)': 15,
            r'click\s*(link|here|below)': 6,
            r'http[s]?://|www\.|bit\.ly': 8,
            r'call\s*0[7-9][0-9]{8,}': 7,
            r'urgent|immediate|action\s*required': 5
        }
        
        for pattern, points in high_risk_patterns.items():
            if re.search(pattern, sms_lower, re.IGNORECASE):
                score += points
                reasons.append(pattern[:30])
        
        # Risk assessment
        if score >= 25:
            message = '🚨 EXTREME RISK - NIGERIAN ADVANCE FEE SCAM DETECTED!'
            result_type = 'scam'
        elif score >= 18:
            message = '🚨 HIGH-RISK SCAM - Likely financial fraud attempt'
            result_type = 'scam'
        elif score >= 12:
            message = '⚠️ SUSPICIOUS - Potential phishing attempt'
            result_type = 'warning'
        elif score >= 8:
            message = '⚠️ CAUTION - Some suspicious elements detected'
            result_type = 'warning'
        else:
            message = '✅ Likely legitimate message'
            result_type = 'safe'
        
        return jsonify({
            'success': True,
            'message': message,
            'type': result_type,
            'risk_score': score
        })
    except Exception as e:
        logger.error(f"SMS check error: {e}")
        return jsonify({'success': False, 'message': 'Server error during SMS check'})

# =============================================
# AUTHENTICATION API ENDPOINTS
# =============================================

@app.route('/api/register-user', methods=['POST'])
def api_register_user():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        phone_number = data.get('phone_number', '').strip()
        name = data.get('name', '').strip()
        
        if not email or not password or not phone_number:
            return jsonify({'success': False, 'message': 'Email, password and phone number are required'})
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'})
        
        if not re.match(r'^0[7-9][0-9]{9}$', phone_number):
            return jsonify({'success': False, 'message': 'Please enter a valid Nigerian phone number'})
        
        # Create user
        user, error = UserManager.create_user(email, password, phone_number, name)
        if error:
            return jsonify({'success': False, 'message': error})
        
        # Generate and send OTP
        if OTPManager.generate_and_send_otp(email):
            return jsonify({
                'success': True,
                'message': 'Registration successful! OTP sent to your email.',
                'user_id': user['id']
            })
        else:
            # Check if email configuration is missing
            sender_email = EMAIL_CONFIG['sender_email']
            sender_password = EMAIL_CONFIG['sender_password']
            if not sender_email or not sender_password:
                logger.error("Email configuration missing - check SMTP_EMAIL and SMTP_PASSWORD environment variables")
                return jsonify({
                    'success': False,
                    'message': 'Email service configuration error. Please contact administrator.'
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! But failed to send OTP. Please use "Verify Email" tab to request a new OTP.'
                })
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'message': 'Server error during registration'})

@app.route('/api/verify-otp', methods=['POST'])
def api_verify_otp():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        otp_code = data.get('otp_code')
        
        if not email or not otp_code:
            return jsonify({'success': False, 'message': 'Email and OTP code are required'})
        
        # Verify OTP
        if OTPManager.verify_otp(email, otp_code):
            # Find user by email and mark as verified
            user = UserManager.get_user_by_email(email)
            if user:
                UserManager.verify_user_email(user['id'])
                
                # Create session after verification
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
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        return jsonify({'success': False, 'message': 'Server error during OTP verification'})

@app.route('/api/send-verification-otp', methods=['POST'])
def api_send_verification_otp():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
        
        # Check if user exists
        user = UserManager.get_user_by_email(email)
        if not user:
            return jsonify({'success': False, 'message': 'Email not found. Please register first.'})
        
        # Check if already verified
        if user.get('is_verified', False):
            return jsonify({'success': False, 'message': 'Email is already verified'})
        
        # Generate and send OTP
        if OTPManager.generate_and_send_otp(email):
            return jsonify({
                'success': True,
                'message': 'OTP sent to your email!'
            })
        else:
            # Check if email configuration is missing
            sender_email = EMAIL_CONFIG['sender_email']
            sender_password = EMAIL_CONFIG['sender_password']
            if not sender_email or not sender_password:
                return jsonify({
                    'success': False,
                    'message': 'Email service not configured. Please contact administrator.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to send OTP. Please try again.'
                })
    except Exception as e:
        logger.error(f"Send verification OTP error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/resend-otp', methods=['POST'])
def api_resend_otp():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
        
        if OTPManager.generate_and_send_otp(email):
            return jsonify({'success': True, 'message': 'New OTP sent to your email'})
        else:
            # Check if email configuration is missing
            sender_email = EMAIL_CONFIG['sender_email']
            sender_password = EMAIL_CONFIG['sender_password']
            if not sender_email or not sender_password:
                return jsonify({
                    'success': False,
                    'message': 'Email service not configured. Please contact administrator.'
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to send OTP'})
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/login-user', methods=['POST'])
def api_login_user():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'})
        
        user = UserManager.authenticate_user(email, password)
        if user:
            # Check if email is verified
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
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Server error during login'})

@app.route('/api/validate-session', methods=['POST'])
def api_validate_session():
    try:
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
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    try:
        data = request.get_json()
        session_token = data.get('session_token')
        
        if AuthManager.logout_session(session_token):
            return jsonify({'success': True, 'message': 'Logged out successfully'})
        else:
            return jsonify({'success': False, 'message': 'Logout failed'})
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

# =============================================
# PASSWORD RESET ENDPOINTS
# =============================================

@app.route('/api/forgot-password', methods=['POST'])
def api_forgot_password():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
        
        user = UserManager.get_user_by_email(email)
        if not user:
            # Don't reveal if email exists for security
            return jsonify({
                'success': True, 
                'message': 'If the email exists, a password reset link has been sent.'
            })
        
        reset_token = UserManager.create_password_reset_token(email)
        if not reset_token:
            return jsonify({'success': False, 'message': 'Failed to create reset token'})
        
        if EmailService.send_password_reset_email(email, reset_token):
            return jsonify({
                'success': True,
                'message': 'Password reset link sent to your email!'
            })
        else:
            # Check if email configuration is missing
            sender_email = EMAIL_CONFIG['sender_email']
            sender_password = EMAIL_CONFIG['sender_password']
            if not sender_email or not sender_password:
                return jsonify({
                    'success': False,
                    'message': 'Email service not configured. Please contact administrator.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to send reset email. Please try again.'
                })
    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    try:
        data = request.get_json()
        token = data.get('token')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not token or not new_password or not confirm_password:
            return jsonify({'success': False, 'message': 'All fields are required'})
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'})
        
        # Find user by reset token
        users = UserManager.get_all_users()
        user_email = None
        for user in users.values():
            if 'reset_tokens' in user:
                for reset_token in user['reset_tokens']:
                    if (reset_token['token'] == token and 
                        not reset_token['used'] and 
                        datetime.now() < datetime.fromisoformat(reset_token['expires_at'])):
                        user_email = user['email']
                        break
            if user_email:
                break
        
        if not user_email:
            return jsonify({'success': False, 'message': 'Invalid or expired reset token'})
        
        # Update password
        if UserManager.update_password(user_email, new_password):
            # Mark token as used
            UserManager.use_reset_token(user_email, token)
            
            return jsonify({
                'success': True,
                'message': 'Password reset successfully! You can now login with your new password.'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to reset password'})
    except Exception as e:
        logger.error(f"Reset password error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

# =============================================
# USER MANAGEMENT ENDPOINTS
# =============================================

@app.route('/api/user-stats', methods=['GET'])
def api_user_stats():
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID is required'})
        
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
            'success': True,
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
    except Exception as e:
        logger.error(f"User stats error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

# =============================================
# PAYMENT ENDPOINTS
# =============================================

@app.route('/api/initiate-payment', methods=['POST'])
def api_initiate_payment():
    try:
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
        if not payment:
            return jsonify({'success': False, 'message': 'Failed to create payment'})
        
        return jsonify({
            'success': True,
            'payment_id': payment['id'],
            'message': 'Payment initiated successfully'
        })
    except Exception as e:
        logger.error(f"Initiate payment error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/check-payment-status', methods=['GET'])
def api_check_payment_status():
    try:
        payment_id = request.args.get('payment_id')
        user_id = request.args.get('user_id')
        
        if not payment_id or not user_id:
            return jsonify({'success': False, 'message': 'Payment ID and User ID are required'})
        
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
    except Exception as e:
        logger.error(f"Check payment status error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

# =============================================
# ADMIN ENDPOINTS
# =============================================

@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    try:
        users = UserManager.get_all_users()
        return jsonify(users)
    except Exception as e:
        logger.error(f"Admin users error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/admin/payments', methods=['GET'])
def api_admin_payments():
    try:
        payments = PaymentManager.get_all_payments()
        return jsonify(payments)
    except Exception as e:
        logger.error(f"Admin payments error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/admin/verify-payment', methods=['POST'])
def api_admin_verify_payment():
    try:
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
    except Exception as e:
        logger.error(f"Admin verify payment error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@app.route('/api/admin/activate-premium', methods=['POST'])
def api_admin_activate_premium():
    try:
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
    except Exception as e:
        logger.error(f"Admin activate premium error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

# =============================================
# DEBUG & HEALTH CHECK ENDPOINTS
# =============================================

@app.route('/api/debug-db')
def debug_db():
    """Test MongoDB connection"""
    try:
        db = Database.get_db()
        users_count = len(Database.load_users())
        payments_count = len(Database.load_payments())
        
        return jsonify({
            'success': True,
            'mongodb_connected': db is not None,
            'total_users': users_count,
            'total_payments': payments_count,
            'database_name': db.name if db else 'None',
            'collections': db.list_collection_names() if db else [],
            'environment': 'production' if os.environ.get('MONGODB_URI') else 'development'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

# =============================================
# DEBUG ENDPOINTS
# =============================================

@app.route('/api/debug-mongo', methods=['GET'])
def debug_mongo():
    """Debug MongoDB connection with more details"""
    import urllib.parse
    
    mongo_uri = os.environ.get('MONGODB_URI')
    
    # Mask password for security
    masked_uri = "NOT SET"
    if mongo_uri:
        if '@' in mongo_uri:
            parts = mongo_uri.split('@')
            user_part = parts[0]
            if ':' in user_part:
                user_pass = user_part.split(':')
                masked_uri = user_pass[0] + ':••••••••@' + parts[1]
        else:
            masked_uri = mongo_uri
    
    try:
        # Test connection
        db = Database.get_db()
        if db:
            return jsonify({
                'success': True,
                'message': 'MongoDB connected',
                'database': db.name,
                'collections': db.list_collection_names(),
                'connection_string_masked': masked_uri,
                'password_set': bool(os.environ.get('MONGODB_URI')),
                'environment': 'Vercel' if 'VERCEL' in os.environ else 'Local'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'MongoDB not connected',
                'connection_string_masked': masked_uri,
                'password_set': bool(os.environ.get('MONGODB_URI')),
                'environment': 'Vercel' if 'VERCEL' in os.environ else 'Local'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'connection_string_masked': masked_uri,
            'password_set': bool(os.environ.get('MONGODB_URI')),
            'environment': 'Vercel' if 'VERCEL' in os.environ else 'Local'
        })

@app.route('/api/test-email', methods=['GET'])
def test_email():
    """Test email configuration"""
    sender_email = EMAIL_CONFIG['sender_email']
    sender_password = EMAIL_CONFIG['sender_password']
    
    return jsonify({
        'email_configured': bool(sender_email and sender_password),
        'sender_email_set': bool(sender_email),
        'sender_password_set': bool(sender_password),
        'sender_email': sender_email[:3] + '••••••' if sender_email else None
    })


@app.route('/api/test-mongo', methods=['GET'])
def test_mongo():
    """Simple MongoDB test endpoint"""
    try:
        db = Database.get_db()
        if not db:
            return jsonify({
                'status': 'error',
                'message': 'Database not connected'
            }), 500
        
        # Test by listing collections
        collections = db.list_collection_names()
        
        return jsonify({
            'status': 'success',
            'message': 'MongoDB connected via Vercel',
            'database': db.name,
            'collections': collections,
            'collection_count': len(collections)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/favicon.ico')
def favicon():
    return '', 204

# =============================================
# APPLICATION STARTUP
# =============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8001))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info("🚀 Starting CyberGuard NG Server")
    
    # Check for Vercel MongoDB connection
    logger.info("🔍 Checking database connection...")
    
    if 'MONGODB_URI' in os.environ:
        logger.info("✅ MONGODB_URI environment variable found")
        logger.info(f"📦 Database name: atlas-purple-book")
        
        # Test connection - use 'is not None' instead of truth testing
        db = Database.get_db()
        if db is not None:
            logger.info(f"✅ Connected to Vercel MongoDB Atlas successfully!")
            try:
                # Check if it's MongoDB database object
                if hasattr(db, 'name'):
                    logger.info(f"📊 Database: {db.name}")
                if hasattr(db, 'list_collection_names'):
                    collections = db.list_collection_names()
                    logger.info(f"📁 Collections: {collections}")
            except Exception as e:
                logger.warning(f"⚠️ Could not get database info: {e}")
        else:
            logger.warning("⚠️ Could not connect to MongoDB - using in-memory fallback")
    else:
        logger.warning("⚠️ MONGODB_URI not found - using in-memory storage")
    
    # Check email configuration
    if EMAIL_CONFIG['sender_email'] and EMAIL_CONFIG['sender_password']:
        logger.info(f"✅ Email service configured for: {EMAIL_CONFIG['sender_email']}")
    else:
        logger.warning("⚠️ Email configuration missing - password reset won't work")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
