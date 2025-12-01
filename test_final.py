# Save as test_final.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_app_password():
    print("Testing Gmail SMTP with App Password...")
    print("=" * 50)
    
    try:
        # Your credentials
        sender_email = "aliyuhaydal9@gmail.com"
        app_password = "ujppworxhprdbbjd"  # No spaces!
        
        print(f"Email: {sender_email}")
        print(f"App Password (first 4 chars): {app_password[:4]}...")
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = sender_email
        msg['Subject'] = "✅ CyberGuard - App Password Test Successful!"
        
        body = """
        Congratulations! Your App Password is working correctly.
        
        This means:
        1. ✅ Email service is configured properly
        2. ✅ Your CyberGuard app can now send emails
        3. ✅ Users will receive OTP codes for verification
        4. ✅ Password reset functionality will work
        
        Next steps:
        1. Test user registration in your app
        2. Check that OTP emails arrive
        3. Deploy to Vercel
        
        Best regards,
        CyberGuard Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        print("\nConnecting to Gmail SMTP...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        print("TLS encryption enabled...")
        
        print("Logging in with App Password...")
        server.login(sender_email, app_password)
        print("✅ Login successful!")
        
        print("Sending test email...")
        server.send_message(msg)
        server.quit()
        
        print("\n" + "=" * 50)
        print("✅ SUCCESS! Test email sent!")
        print("📧 Check your inbox: aliyuhaydal9@gmail.com")
        print("📧 Also check spam folder if not in inbox")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 50)
        print("❌ FAILED!")
        print(f"Error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure there are NO spaces in the App Password")
        print("2. The password should be exactly: ujppworxhprdbbjd")
        print("3. Wait 5 minutes after generating App Password")
        print("4. Ensure 2-Step Verification is enabled")
        print("=" * 50)
        return False

if __name__ == "__main__":
    test_app_password()
