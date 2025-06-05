from flask import Flask, render_template_string, request, redirect, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
import io
import base64
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'athena-museum-secret-key')

# Firebase Configuration using environment variables
def init_firebase():
    if not firebase_admin._apps:
        try:
            # Use environment variables for Firebase credentials
            firebase_config = {
                "type": "service_account",
                "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
                "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
                "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
                "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ.get('FIREBASE_CLIENT_EMAIL', '').replace('@', '%40')}",
                "universe_domain": "googleapis.com"
            }
            
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Firebase initialization error: {e}")
            return None
    
    return firestore.client()

# Initialize Firebase
db = init_firebase()

# SMTP Configuration from environment variables
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

# Enhanced HTML Template with 3D Effects
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Athena Museum - Payment Portal</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary-color: #6c63ff;
            --secondary-color: #764ba2;
            --accent-color: #ff6b6b;
            --text-color: #ffffff;
            --bg-dark: #0f172a;
            --bg-card: rgba(255, 255, 255, 0.05);
            --border-color: rgba(255, 255, 255, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            color: var(--text-color);
            overflow-x: hidden;
            position: relative;
        }

        /* Animated Background */
        .bg-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            overflow: hidden;
        }

        .bg-animation span {
            position: absolute;
            display: block;
            width: 20px;
            height: 20px;
            background: rgba(255, 255, 255, 0.05);
            animation: animate 25s linear infinite;
            bottom: -150px;
            border-radius: 50%;
        }

        .bg-animation span:nth-child(1) { left: 25%; width: 80px; height: 80px; animation-delay: 0s; }
        .bg-animation span:nth-child(2) { left: 10%; width: 20px; height: 20px; animation-delay: 2s; animation-duration: 12s; }
        .bg-animation span:nth-child(3) { left: 70%; width: 20px; height: 20px; animation-delay: 4s; }
        .bg-animation span:nth-child(4) { left: 40%; width: 60px; height: 60px; animation-delay: 0s; animation-duration: 18s; }
        .bg-animation span:nth-child(5) { left: 65%; width: 20px; height: 20px; animation-delay: 0s; }
        .bg-animation span:nth-child(6) { left: 75%; width: 110px; height: 110px; animation-delay: 3s; }
        .bg-animation span:nth-child(7) { left: 35%; width: 150px; height: 150px; animation-delay: 7s; }
        .bg-animation span:nth-child(8) { left: 50%; width: 25px; height: 25px; animation-delay: 15s; animation-duration: 45s; }
        .bg-animation span:nth-child(9) { left: 20%; width: 15px; height: 15px; animation-delay: 2s; animation-duration: 35s; }
        .bg-animation span:nth-child(10) { left: 85%; width: 150px; height: 150px; animation-delay: 0s; animation-duration: 11s; }

        @keyframes animate {
            0% { transform: translateY(0) rotate(0deg); opacity: 1; border-radius: 50%; }
            100% { transform: translateY(-1000px) rotate(720deg); opacity: 0; border-radius: 50%; }
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
            z-index: 1;
        }

        .header {
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }

        .header h1 {
            font-size: clamp(2.5rem, 5vw, 4rem);
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #6c63ff, #764ba2, #ff6b6b);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
            display: inline-block;
        }

        .header h1::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 4px;
            background: linear-gradient(to right, #6c63ff, #764ba2);
            border-radius: 2px;
        }

        .header p {
            font-size: 1.2rem;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 1rem;
        }

        .card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            transform-style: preserve-3d;
            perspective: 1000px;
            transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent);
            transition: 0.5s;
        }

        .card:hover::before { left: 100%; }
        .card:hover {
            transform: translateY(-10px) rotateX(5deg);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .card h2 {
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
            color: #fff;
            text-align: center;
            position: relative;
            padding-bottom: 0.5rem;
        }

        .card h2::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 50px;
            height: 3px;
            background: linear-gradient(to right, var(--primary-color), var(--secondary-color));
            border-radius: 2px;
        }

        .form-group {
            margin-bottom: 1.5rem;
            position: relative;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 1rem;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.8);
        }

        .form-control {
            width: 100%;
            padding: 1rem 1.5rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            color: #fff;
            font-size: 1rem;
            transition: all 0.3s ease;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.2);
            background: rgba(255, 255, 255, 0.1);
        }

        .form-control::placeholder { color: rgba(255, 255, 255, 0.4); }

        .btn {
            display: inline-block;
            padding: 1rem 2rem;
            background: linear-gradient(45deg, var(--primary-color), var(--secondary-color));
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
            text-decoration: none;
            position: relative;
            overflow: hidden;
            z-index: 1;
            width: 100%;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(45deg, var(--secondary-color), var(--primary-color));
            z-index: -1;
            transition: opacity 0.3s ease;
            opacity: 0;
        }

        .btn:hover::before { opacity: 1; }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(108, 99, 255, 0.3);
        }
        .btn:active { transform: translateY(-1px); }

        .btn-accent {
            background: linear-gradient(45deg, var(--accent-color), #ff8e8e);
        }

        .btn-accent::before {
            background: linear-gradient(45deg, #ff8e8e, var(--accent-color));
        }

        .booking-details { margin-top: 2rem; }

        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 1rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .detail-row:last-child { border-bottom: none; }

        .detail-label {
            font-weight: 500;
            color: rgba(255, 255, 255, 0.7);
        }

        .detail-value {
            font-weight: 600;
            color: #fff;
        }

        .status-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-pending { background: linear-gradient(45deg, #f39c12, #e67e22); color: white; }
        .status-completed { background: linear-gradient(45deg, #2ecc71, #27ae60); color: white; }
        .status-expired { background: linear-gradient(45deg, #e74c3c, #c0392b); color: white; }

        .qr-container {
            margin-top: 2rem;
            text-align: center;
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transform: perspective(1000px);
            transition: all 0.3s ease;
        }

        .qr-container:hover { transform: perspective(1000px) rotateX(5deg); }
        .qr-container h3 { color: #333; margin-bottom: 1rem; }
        .qr-container img {
            max-width: 200px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }

        .alert {
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        }

        .alert::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
        }

        .alert-success {
            background: rgba(46, 204, 113, 0.1);
            border: 1px solid rgba(46, 204, 113, 0.3);
            color: #2ecc71;
        }

        .alert-success::before { background: #2ecc71; }

        .alert-error {
            background: rgba(231, 76, 60, 0.1);
            border: 1px solid rgba(231, 76, 60, 0.3);
            color: #e74c3c;
        }

        .alert-error::before { background: #e74c3c; }

        .museum-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 3rem;
        }

        .info-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }

        .info-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            border-color: rgba(255, 255, 255, 0.2);
        }

        .info-card h3 {
            font-size: 1.2rem;
            margin-bottom: 1rem;
            color: #fff;
            display: flex;
            align-items: center;
        }

        .info-card h3 span {
            margin-right: 0.5rem;
            font-size: 1.5rem;
        }

        .info-card p {
            color: rgba(255, 255, 255, 0.7);
            line-height: 1.6;
        }

        .success-animation { text-align: center; margin-bottom: 2rem; }

        .checkmark {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: block;
            stroke-width: 2;
            stroke: #2ecc71;
            stroke-miterlimit: 10;
            margin: 0 auto 1rem;
            box-shadow: inset 0px 0px 0px #2ecc71;
            animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s both;
        }

        .checkmark__circle {
            stroke-dasharray: 166;
            stroke-dashoffset: 166;
            stroke-width: 2;
            stroke-miterlimit: 10;
            stroke: #2ecc71;
            fill: none;
            animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;
        }

        .checkmark__check {
            transform-origin: 50% 50%;
            stroke-dasharray: 48;
            stroke-dashoffset: 48;
            animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;
        }

        @keyframes stroke { 100% { stroke-dashoffset: 0; } }
        @keyframes scale { 0%, 100% { transform: none; } 50% { transform: scale3d(1.1, 1.1, 1); } }
        @keyframes fill { 100% { box-shadow: inset 0px 0px 0px 30px #2ecc71; } }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
            margin-right: 10px;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .card { padding: 1.5rem; }
            .header h1 { font-size: 2rem; }
            .header p { font-size: 1rem; }
            .museum-info { grid-template-columns: 1fr; }
        }

        .tilt-card {
            transform-style: preserve-3d;
            transform: perspective(1000px);
        }

        .tilt-content {
            transform: translateZ(30px);
            transition: all 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="bg-animation">
        <span></span><span></span><span></span><span></span><span></span>
        <span></span><span></span><span></span><span></span><span></span>
    </div>

    <div class="container">
        <div class="header">
            <h1>🏛️ Athena Museum</h1>
            <p>Complete Your Booking Payment</p>
        </div>

        {% if page == 'home' %}
        <div class="card tilt-card" id="tiltCard">
            <div class="tilt-content">
                <h2>Find Your Booking</h2>
                <form method="POST" action="/validate" id="emailForm">
                    <div class="form-group">
                        <label for="email">📧 Email Address</label>
                        <input type="email" id="email" name="email" class="form-control" 
                               placeholder="Enter your email address" required>
                    </div>
                    <button type="submit" class="btn" id="submitBtn">
                        🔍 Find My Booking
                    </button>
                </form>
            </div>
        </div>

        {% elif page == 'booking' %}
        <div class="card tilt-card" id="tiltCard">
            <div class="tilt-content">
                <h2>Booking Details</h2>
                
                <div class="booking-details">
                    <div class="detail-row">
                        <span class="detail-label">📧 Email:</span>
                        <span class="detail-value">{{ booking.email }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">📱 Phone:</span>
                        <span class="detail-value">{{ booking.phone }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">🎫 Tickets:</span>
                        <span class="detail-value">{{ booking.tickets }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">💰 Amount:</span>
                        <span class="detail-value">₹{{ booking.amount }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">📅 Valid Until:</span>
                        <span class="detail-value">{{ booking.validity_str }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">📊 Status:</span>
                        <span class="detail-value">
                            <span class="status-badge status-{{ booking.status }}">{{ booking.status.title() }}</span>
                        </span>
                    </div>
                </div>

                {% if booking.status == 'pending' %}
                <form method="POST" action="/process_payment" id="paymentForm">
                    <input type="hidden" name="email" value="{{ booking.email }}">
                    <button type="submit" class="btn btn-accent" id="payBtn">
                        💳 Complete Payment Now
                    </button>
                </form>
                {% endif %}

                {% if booking.status == 'completed' and booking.qr_code %}
                <div class="qr-container">
                    <h3>📱 Your Entry QR Code</h3>
                    <img src="data:image/png;base64,{{ booking.qr_code }}" alt="QR Code">
                    <p style="margin-top: 15px; color: #666;">Present this QR code at the museum entrance</p>
                    <p style="margin-top: 10px; color: #999; font-size: 0.9rem;">Booking ID: {{ booking.booking_id }}</p>
                </div>
                {% endif %}
            </div>
        </div>

        {% elif page == 'success' %}
        <div class="card tilt-card" id="tiltCard">
            <div class="tilt-content">
                <div class="success-animation">
                    <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                        <circle class="checkmark__circle" cx="26" cy="26" r="25" fill="none"/>
                        <path class="checkmark__check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                    </svg>
                    <h2>Payment Successful!</h2>
                </div>
                
                <div class="alert alert-success">
                    Your booking has been confirmed! We've sent your e-ticket with QR code to your email.
                </div>
                
                <a href="/booking/{{ email }}" class="btn">
                    📱 View Your Ticket
                </a>
            </div>
        </div>

        {% elif page == 'error' %}
        <div class="card tilt-card" id="tiltCard">
            <div class="tilt-content">
                <div class="error-animation">
                    <div class="error-circle">
                        <span style="font-size: 2.5rem;">❌</span>
                    </div>
                    <h2>Booking Not Found</h2>
                </div>
                
                <div class="alert alert-error">
                    {{ error_message }}
                </div>
                
                <a href="/" class="btn">
                    🔍 Try Again
                </a>
            </div>
        </div>
        {% endif %}

        <div class="museum-info">
            <div class="info-card">
                <h3><span>🏛️</span> Location</h3>
                <p>123 Science Avenue<br>Mumbai, Maharashtra 400001<br>India</p>
            </div>
            <div class="info-card">
                <h3><span>🕒</span> Opening Hours</h3>
                <p>Monday - Saturday: 9:00 AM - 5:00 PM<br>Sunday: 10:00 AM - 4:00 PM</p>
            </div>
            <div class="info-card">
                <h3><span>📞</span> Contact</h3>
                <p>Phone: +91 22 1234 5678<br>Email: info@athenamuseum.com</p>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const tiltCard = document.getElementById('tiltCard');
            
            if (tiltCard) {
                tiltCard.addEventListener('mousemove', function(e) {
                    const rect = this.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    
                    const centerX = rect.width / 2;
                    const centerY = rect.height / 2;
                    
                    const angleX = (y - centerY) / 20;
                    const angleY = (centerX - x) / 20;
                    
                    this.style.transform = `perspective(1000px) rotateX(${angleX}deg) rotateY(${angleY}deg)`;
                });
                
                tiltCard.addEventListener('mouseleave', function() {
                    this.style.transform = 'perspective(1000px) rotateX(0) rotateY(0)';
                });
            }
            
            const emailForm = document.getElementById('emailForm');
            const paymentForm = document.getElementById('paymentForm');
            const submitBtn = document.getElementById('submitBtn');
            const payBtn = document.getElementById('payBtn');
            
            if (emailForm && submitBtn) {
                emailForm.addEventListener('submit', function() {
                    submitBtn.innerHTML = '<span class="loading"></span> Searching...';
                    submitBtn.disabled = true;
                });
            }
            
            if (paymentForm && payBtn) {
                paymentForm.addEventListener('submit', function() {
                    payBtn.innerHTML = '<span class="loading"></span> Processing Payment...';
                    payBtn.disabled = true;
                });
            }
        });
    </script>
</body>
</html>
'''

# Helper Functions
def get_booking_by_email(email):
    """Get booking from Firebase by email"""
    if not db:
        return None
    
    try:
        email_doc_id = email.replace('.', '_').replace('@', '_at_')
        booking_doc = db.collection('bookings').document(email_doc_id).get()
        
        if not booking_doc.exists:
            return None
        
        booking_data = booking_doc.to_dict()
        
        # Calculate validity status
        validity_date = booking_data.get('validity')
        current_time = datetime.now()
        
        if validity_date:
            if hasattr(validity_date, 'replace'):
                validity_datetime = validity_date.replace(tzinfo=None)
            else:
                validity_datetime = validity_date
            
            is_valid = validity_datetime > current_time
            validity_str = validity_datetime.strftime('%d %b %Y, %H:%M')
            
            if is_valid:
                time_remaining = validity_datetime - current_time
                hours_remaining = int(time_remaining.total_seconds() // 3600)
                minutes_remaining = int((time_remaining.total_seconds() % 3600) // 60)
                validity_str += f" ({hours_remaining}h {minutes_remaining}m remaining)"
            else:
                validity_str += " (EXPIRED)"
        else:
            is_valid = False
            validity_str = "Not set"
        
        booking_data['validity_str'] = validity_str
        booking_data['is_valid'] = is_valid
        
        # Generate QR code if completed
        if booking_data.get('status') == 'completed' and booking_data.get('booking_id') and booking_data.get('hash'):
            qr_code = generate_qr_code(booking_data['booking_id'], booking_data['hash'])
            booking_data['qr_code'] = qr_code
        
        return booking_data
        
    except Exception as e:
        print(f"Error fetching booking: {e}")
        return None

def generate_qr_code(booking_id, hash_code):
    """Generate QR code for booking"""
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
        img.save(buffered)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
    except Exception as e:
        print(f"QR code generation failed: {e}")
        return None

def send_confirmation_email(booking_data):
    """Send confirmation email with QR code"""
    try:
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print("SMTP credentials not configured")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = booking_data['email']
        msg['Subject'] = "Athena Museum - Booking Confirmed"
        
        # Generate QR code for email
        qr_code = generate_qr_code(booking_data['booking_id'], booking_data['hash'])
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #6c63ff, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ padding: 30px; background: #f8f9fa; }}
                .footer {{ background: #e9ecef; padding: 20px; text-align: center; font-size: 14px; border-radius: 0 0 10px 10px; }}
                .ticket {{ background: white; border: 2px dashed #ccc; padding: 20px; margin: 20px 0; border-radius: 10px; text-align: center; }}
                .qr-code {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏛️ Athena Museum</h1>
                    <h2>Booking Confirmed!</h2>
                </div>
                <div class="content">
                    <p>Dear Visitor,</p>
                    <p>Your payment has been processed successfully! Here are your booking details:</p>
                    
                    <div class="ticket">
                        <h3>Your E-Ticket</h3>
                        <div class="qr-code">
                            <img src="data:image/png;base64,{qr_code}" alt="QR Code" style="max-width: 200px;">
                        </div>
                        <p><strong>Booking ID:</strong> {booking_data['booking_id']}</p>
                        <p><strong>Tickets:</strong> {booking_data['tickets']}</p>
                        <p><strong>Amount:</strong> ₹{booking_data['amount']}</p>
                        <p><strong>Valid Until:</strong> {booking_data['validity_str']}</p>
                    </div>
                    
                    <p>Present the QR code above at the museum entrance for entry.</p>
                    <p>We look forward to your visit!</p>
                </div>
                <div class="footer">
                    <p><strong>Athena Museum of Science and Technology</strong></p>
                    <p>123 Science Avenue, Mumbai, Maharashtra 400001, India</p>
                    <p>📞 +91 22 1234 5678 | 📧 info@athenamuseum.com</p>
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
        print(f"Failed to send email: {e}")
        return False

def process_payment(email):
    """Process payment and update booking"""
    if not db:
        return False, "Database connection failed"
    
    try:
        # Generate booking ID and hash
        booking_id = f"ATH{datetime.now().strftime('%Y%m%d')}{str(int(datetime.now().timestamp()))[-6:]}"
        hash_code = hashlib.md5(f"{booking_id}{email}".encode()).hexdigest()[:8].upper()
        
        # Update booking in Firebase
        email_doc_id = email.replace('.', '_').replace('@', '_at_')
        booking_ref = db.collection('bookings').document(email_doc_id)
        
        booking_ref.update({
            'status': 'completed',
            'booking_id': booking_id,
            'hash': hash_code,
            'updated_at': datetime.now()
        })
        
        # Create payment record
        db.collection('payments').document(booking_id).set({
            'booking_id': booking_id,
            'email': email,
            'status': 'completed',
            'created_at': datetime.now()
        })
        
        # Get updated booking data
        booking_data = get_booking_by_email(email)
        
        # Send confirmation email
        if booking_data:
            send_confirmation_email(booking_data)
        
        return True, "Payment processed successfully"
        
    except Exception as e:
        print(f"Payment processing error: {e}")
        return False, f"Payment failed: {str(e)}"

# Routes
@app.route('/', methods=['GET'])
def home():
    email = request.args.get('email', '')
    if email:
        return redirect(f"/booking/{email}")
    return render_template_string(HTML_TEMPLATE, page='home')

@app.route('/validate', methods=['POST'])
def validate_email():
    email = request.form.get('email', '').strip()
    
    if not email:
        return render_template_string(HTML_TEMPLATE, page='error', 
                                    error_message="Please enter a valid email address.")
    
    booking = get_booking_by_email(email)
    
    if not booking:
        return render_template_string(HTML_TEMPLATE, page='error',
                                    error_message="No booking found for this email address. Please check and try again.")
    
    return redirect(f"/booking/{email}")

@app.route('/booking/<email>', methods=['GET'])
def booking_details(email):
    booking = get_booking_by_email(email)
    
    if not booking:
        return render_template_string(HTML_TEMPLATE, page='error',
                                    error_message="Booking not found or has expired.")
    
    return render_template_string(HTML_TEMPLATE, page='booking', booking=booking)

@app.route('/process_payment', methods=['POST'])
def process_payment_route():
    email = request.form.get('email', '').strip()
    
    if not email:
        return render_template_string(HTML_TEMPLATE, page='error',
                                    error_message="Invalid request.")
    
    success, message = process_payment(email)
    
    if success:
        return render_template_string(HTML_TEMPLATE, page='success', email=email)
    else:
        return render_template_string(HTML_TEMPLATE, page='error',
                                    error_message=message)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Vercel serverless function handler
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)