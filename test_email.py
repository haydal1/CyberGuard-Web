import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_smtp():
    try:
        sender_email = "aliyuhaydal9@gmail.com"
        sender_password = "naukmhqqnyrtmxf"
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = sender_email  # Send to yourself for testing
        msg['Subject'] = "Test Email from CyberGuard"
        
        body = "This is a test email from CyberGuard application."
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        print("Testing SMTP connection...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print("✅ Test email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ SMTP Error: {e}")
        return False

if __name__ == "__main__":
    test_smtp()
