"""
YOUR ACTUAL BUSINESS CONFIGURATION
Update these with your real details
"""

# YOUR BANK ACCOUNT DETAILS
YOUR_BANK_DETAILS = {
    'bank_name': 'ZenithBank',  # Change to your actual bank
    'account_number': '4249996702',  # Change to your actual account number
    'account_name': 'Aliyu Egwa Usman',  # Change to your actual name
    'bank_code': '966'  # GTBank code, change if different bank
}

# YOUR CONTACT INFORMATION
YOUR_CONTACT = {
    'whatsapp_number': '09031769476',  # Change to your WhatsApp
    'business_name': 'aliyuhaydar',
    'customer_support': 'aliyuhaydal9@gmail.com'  # Change to your email
}

# YOUR PRICING (you can adjust these)
YOUR_PRICING = {
    'daily': {
        'price': 200,
        'duration_days': 1,
        'description': '24 hours unlimited access'
    },
    'weekly': {
        'price': 1000, 
        'duration_days': 7,
        'description': '7 days unlimited access'
    },
    'monthly': {
        'price': 3000,
        'duration_days': 30,
        'description': '30 days unlimited access'
    }
}

# PAYMENT VALIDATION SETTINGS
PAYMENT_SETTINGS = {
    'validation_required': True,
    'whatsapp_verification': True,
    'auto_approve_after_hours': 24,  # Auto-approve if no response in 24h
    'screenshot_required': True
}

print("⚠️  IMPORTANT: Update business_config.py with YOUR actual details!")
print("📍 Bank account, WhatsApp number, and pricing need to be customized")
