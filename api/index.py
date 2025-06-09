from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import qrcode
import io
import base64
from datetime import datetime
import os
import json

app = Flask(__name__)

# Initialize Firebase
def init_firebase():
    try:
        if not firebase_admin._apps:
            # Try to get Firebase config from environment variables
            firebase_config = {
                "type": os.environ.get("FIREBASE_TYPE", "service_account"),
                "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_X509_CERT_URL"),
                "universe_domain": "googleapis.com"
            }
            
            # Check if all required fields are present
            if all(firebase_config.values()):
                cred = credentials.Certificate(firebase_config)
                firebase_admin.initialize_app(cred)
                return firestore.client()
            else:
                print("Firebase environment variables not found")
                return None
    except Exception as e:
        print(f"Firebase initialization error: {e}")
        return None

db = init_firebase()

# SMTP Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "chsantosh2004@gmail.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "kzka uohw hbxg gwgi")

def generate_booking_id():
    """Generate a unique booking ID"""
    return f"ATH{random.randint(100000, 999999)}"

def generate_hash(booking_id, email):
    """Generate a security hash for the booking"""
    data = f"{booking_id}{email}{datetime.now().isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def generate_qr_code(booking_id, hash_code):
    """Generate QR code for the booking"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"ATHENA-MUSEUM-{booking_id}-{hash_code}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
    except Exception as e:
        print(f"QR code generation failed: {e}")
        return None

def send_confirmation_email(email, booking_data, qr_code_base64):
    """Send confirmation email with QR code"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = email
        msg['Subject'] = "🎫 Athena Museum - Payment Confirmed & QR Code"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Montserrat', sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
                .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 15px 15px 0 0; }}
                .content {{ padding: 30px; background: white; border-radius: 0 0 15px 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
                .qr-section {{ text-align: center; background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .qr-code {{ max-width: 200px; border: 3px solid #667eea; border-radius: 10px; padding: 10px; background: white; }}
                .details {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .success-badge {{ background: #4caf50; color: white; padding: 10px 20px; border-radius: 25px; display: inline-block; font-weight: bold; }}
                .important {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Athena Museum</h1>
                    <div class="success-badge">✅ Payment Confirmed!</div>
                </div>
                <div class="content">
                    <h2>🎉 Congratulations! Your booking is confirmed</h2>
                    <p>Dear Visitor,</p>
                    <p>Thank you for your payment! Your museum tickets are now confirmed and ready to use.</p>
                    
                    <div class="details">
                        <h3>📋 Booking Details</h3>
                        <p><strong>Booking ID:</strong> {booking_data['booking_id']}</p>
                        <p><strong>Email:</strong> {booking_data['email']}</p>
                        <p><strong>Phone:</strong> {booking_data['phone']}</p>
                        <p><strong>Number of Tickets:</strong> {booking_data['tickets']}</p>
                        <p><strong>Total Amount Paid:</strong> ₹{booking_data['amount']}</p>
                        <p><strong>Security Hash:</strong> {booking_data['hash']}</p>
                        <p><strong>Valid Until:</strong> {booking_data['validity']}</p>
                    </div>
                    
                    <div class="qr-section">
                        <h3>📱 Your Entry QR Code</h3>
                        <img src="data:image/png;base64,{qr_code_base64}" alt="QR Code" class="qr-code">
                        <p><strong>Present this QR code at the museum entrance</strong></p>
                    </div>
                    
                    <div class="important">
                        <h4>📍 Museum Information</h4>
                        <p><strong>Address:</strong> 123 Science Avenue, Mumbai, Maharashtra 400001, India</p>
                        <p><strong>Hours:</strong> Mon-Sat: 9:00 AM - 5:00 PM, Sunday: 10:00 AM - 4:00 PM</p>
                        <p><strong>Contact:</strong> +91 22 1234 5678</p>
                    </div>
                    
                    <div class="important">
                        <h4>⚠️ Important Instructions</h4>
                        <ul>
                            <li>Save this email and QR code on your phone</li>
                            <li>Arrive 15 minutes before your preferred time</li>
                            <li>Bring a valid ID for verification</li>
                            <li>QR code is valid for 24 hours from booking time</li>
                        </ul>
                    </div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <strong>We look forward to welcoming you to the Athena Museum!</strong>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False

@app.route('/')
def payment_page():
    email = request.args.get('email', '')
    
    if not email:
        return redirect('https://update-athena-chatbot.streamlit.app')
    
    # Get booking details from Firebase
    booking_data = None
    if db:
        try:
            email_doc_id = email.replace('.', '_').replace('@', '_at_')
            doc = db.collection('bookings').document(email_doc_id).get()
            if doc.exists:
                booking_data = doc.to_dict()
        except Exception as e:
            print(f"Error fetching booking: {e}")
    
    if not booking_data:
        return redirect('https://update-athena-chatbot.streamlit.app')
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Athena Museum - Payment Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Montserrat', sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: white;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        /* Stylish Back Button */
        .back-button {
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 50px;
            padding: 15px 25px;
            color: white;
            font-weight: 600;
            font-size: 16px;
            cursor: pointer;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .back-button:hover {
            transform: translateY(-3px) scale(1.05);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }
        
        .back-button:active {
            transform: translateY(-1px) scale(1.02);
        }
        
        .back-arrow {
            font-size: 18px;
            transition: transform 0.3s ease;
        }
        
        .back-button:hover .back-arrow {
            transform: translateX(-3px);
        }
        
        /* Floating particles animation */
        .back-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            border-radius: 50px;
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .back-button:hover::before {
            opacity: 1;
        }
        
        .header {
            text-align: center;
            margin: 80px 0 40px 0;
        }
        
        .title {
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 700;
            background: linear-gradient(45deg, #667eea, #764ba2, #4facfe, #00f2fe);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 8s ease infinite;
            margin-bottom: 10px;
        }
        
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .subtitle {
            font-size: 1.2rem;
            color: #b8c6db;
            font-weight: 300;
        }
        
        .payment-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(103, 126, 234, 0.3);
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            margin: 20px 0;
            flex-grow: 1;
        }
        
        .booking-details {
            background: rgba(79, 172, 254, 0.1);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 4px solid #4facfe;
        }
        
        .detail-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .detail-row:last-child {
            border-bottom: none;
            font-weight: 700;
            font-size: 1.2rem;
            color: #4facfe;
        }
        
        .detail-label {
            color: #b8c6db;
            font-weight: 500;
        }
        
        .detail-value {
            color: white;
            font-weight: 600;
        }
        
        .payment-button {
            width: 100%;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border: none;
            border-radius: 15px;
            padding: 20px;
            color: white;
            font-size: 1.2rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 8px 25px rgba(240, 147, 251, 0.4);
            margin-top: 20px;
        }
        
        .payment-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(240, 147, 251, 0.6);
        }
        
        .payment-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .success-message {
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.2), rgba(0, 212, 170, 0.1));
            border: 2px solid #00d4aa;
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            text-align: center;
            display: none;
        }
        
        .success-icon {
            font-size: 3rem;
            margin-bottom: 15px;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .spinner {
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 3px solid #4facfe;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #b8c6db;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            .payment-card {
                padding: 25px;
            }
            
            .back-button {
                top: 15px;
                left: 15px;
                padding: 12px 20px;
                font-size: 14px;
            }
            
            .header {
                margin: 70px 0 30px 0;
            }
        }
    </style>
</head>
<body>
    <a href="https://update-athena-chatbot.streamlit.app" class="back-button">
        <span class="back-arrow">←</span>
        <span>Back to Chatbot</span>
    </a>
    
    <div class="container">
        <div class="header">
            <h1 class="title">🏛️ Athena Museum</h1>
            <p class="subtitle">Secure Payment Gateway</p>
        </div>
        
        <div class="payment-card">
            <h2 style="margin-bottom: 25px; color: #4facfe;">Complete Your Booking</h2>
            
            <div class="booking-details">
                <h3 style="margin-bottom: 20px; color: white;">📋 Booking Summary</h3>
                <div class="detail-row">
                    <span class="detail-label">Email:</span>
                    <span class="detail-value">{{ booking_data.email }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Phone:</span>
                    <span class="detail-value">{{ booking_data.phone }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Number of Tickets:</span>
                    <span class="detail-value">{{ booking_data.tickets }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Total Amount:</span>
                    <span class="detail-value">₹{{ booking_data.amount }}</span>
                </div>
            </div>
            
            <button class="payment-button" onclick="processPayment()">
                💳 Pay ₹{{ booking_data.amount }} Now
            </button>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Processing your payment...</p>
            </div>
            
            <div class="success-message" id="successMessage">
                <div class="success-icon">✅</div>
                <h3>Payment Successful!</h3>
                <p>Your booking has been confirmed. Check your email for the QR code and booking details.</p>
            </div>
        </div>
        
        <div class="footer">
            <p>🔒 Secure payment powered by Athena Museum</p>
            <p>123 Science Avenue, Mumbai, Maharashtra 400001, India</p>
        </div>
    </div>
    
    <script>
        function processPayment() {
            const button = document.querySelector('.payment-button');
            const loading = document.getElementById('loading');
            const successMessage = document.getElementById('successMessage');
            
            // Disable button and show loading
            button.disabled = true;
            button.textContent = 'Processing...';
            loading.style.display = 'block';
            
            // Simulate payment processing
            setTimeout(() => {
                // Call the actual payment processing endpoint
                fetch('/process_payment', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: '{{ booking_data.email }}'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    loading.style.display = 'none';
                    
                    if (data.success) {
                        successMessage.style.display = 'block';
                        button.style.display = 'none';
                        
                        // Redirect to chatbot after 5 seconds
                        setTimeout(() => {
                            window.location.href = 'https://update-athena-chatbot.streamlit.app';
                        }, 5000);
                    } else {
                        button.disabled = false;
                        button.textContent = '💳 Pay ₹{{ booking_data.amount }} Now';
                        alert('Payment failed. Please try again.');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    loading.style.display = 'none';
                    button.disabled = false;
                    button.textContent = '💳 Pay ₹{{ booking_data.amount }} Now';
                    alert('Payment failed. Please try again.');
                });
            }, 2000);
        }
    </script>
</body>
</html>
    """, booking_data=booking_data)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email or not db:
            return jsonify({'success': False, 'error': 'Invalid request'})
        
        # Get booking from Firebase
        email_doc_id = email.replace('.', '_').replace('@', '_at_')
        doc_ref = db.collection('bookings').document(email_doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'success': False, 'error': 'Booking not found'})
        
        booking_data = doc.to_dict()
        
        # Generate booking ID and hash
        booking_id = generate_booking_id()
        hash_code = generate_hash(booking_id, email)
        
        # Generate QR code
        qr_code_base64 = generate_qr_code(booking_id, hash_code)
        
        # Update booking in Firebase
        updated_data = {
            'booking_id': booking_id,
            'hash': hash_code,
            'status': 'completed',
            'payment_date': datetime.now(),
            'updated_at': datetime.now()
        }
        
        doc_ref.update(updated_data)
        
        # Prepare email data
        email_booking_data = {
            'booking_id': booking_id,
            'email': booking_data['email'],
            'phone': booking_data['phone'],
            'tickets': booking_data['tickets'],
            'amount': booking_data['amount'],
            'hash': hash_code,
            'validity': (datetime.now().strftime('%d %b %Y, %H:%M') + ' (24 hours from now)')
        }
        
        # Send confirmation email with QR code
        if qr_code_base64:
            email_sent = send_confirmation_email(email, email_booking_data, qr_code_base64)
        else:
            email_sent = False
        
        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'hash': hash_code,
            'email_sent': email_sent,
            'qr_generated': qr_code_base64 is not None
        })
        
    except Exception as e:
        print(f"Payment processing error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'firebase_connected': db is not None})

if __name__ == '__main__':
    app.run(debug=True)
