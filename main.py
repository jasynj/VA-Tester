import os
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from collections import defaultdict
import uuid
import qrcode
import io
import re


app = Flask(__name__)
@app.route('/')
def home():
    return redirect('/login')

app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret')  # fallback is optional
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///vision_test.db')
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

# ==================== IN-MEMORY SYNC STATE ====================
session_ready = {}
latest_directions = defaultdict(lambda: None)
finished_tests = {}

# ==================== MODELS ====================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    user_uuid = db.Column(db.String(36), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.String(20), nullable=False)

class VisionTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    right_eye_score = db.Column(db.Integer, nullable=False)
    left_eye_score = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== DEVICE DETECTOR ====================
def is_mobile_device(user_agent):
    mobile_regex = re.compile(r"iphone|android|blackberry|mobile|webos", re.IGNORECASE)
    return mobile_regex.search(user_agent) is not None

# ==================== AUTH & USER ROUTES ====================
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data['email']
    password = data['password']
    first_name = data.get('firstName', '')
    last_name = data.get('lastName', '')
    dob = data.get('dob', '')

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 409

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        user_uuid=str(uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Signup successful'})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data['email']
        password = data['password']
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401

        session['user_id'] = user.id

        user_agent = request.headers.get('User-Agent', '')
        if is_mobile_device(user_agent):
            return jsonify({'message': 'Login successful', 'redirect': '/start-test'})
        else:
            return jsonify({'message': 'Login successful', 'redirect': '/dashboard'})

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


# ==================== QR & DASHBOARD ====================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    results = VisionTestResult.query.filter_by(user_id=user.id).order_by(VisionTestResult.timestamp.desc()).all()

    test_results = [
        {
            "date": r.timestamp.strftime('%B %d, %Y at %I:%M %p'),
            "result": (
                f"Right Eye: {r.right_eye_score}/8 ({calculate_visual_acuity(r.right_eye_score)}), "
                f"Left Eye: {r.left_eye_score}/8 ({calculate_visual_acuity(r.left_eye_score)})"
            )
        }
        for r in results
    ]


    session_ready[user.user_uuid] = False

    recommendations = []
    if results:
        latest = results[0]
        if latest.right_eye_score <= 3 or latest.left_eye_score <= 3:
            recommendations.append("⚠️ Schedule a full eye exam. Your results suggest significant vision challenges.")
        elif latest.right_eye_score < 5 or latest.left_eye_score < 5:
            recommendations.append("👓 Consider seeing an optometrist for corrective lenses.")
        elif latest.right_eye_score < 7 or latest.left_eye_score < 7:
            recommendations.append("Your vision may be slightly reduced. Try reading in better light.")
        elif latest.right_eye_score >= 7 and latest.left_eye_score >= 7:
            recommendations.append("✅ Your vision is excellent. Keep up with regular checks!")
        if not recommendations:
            recommendations.append("Monitor your vision and retake the test in 1 month.")

    return render_template(
        "dashboard.html",
        user=user,
        test_results=test_results,
        recommendations=recommendations,
        token=user.user_uuid  
    )


@app.route('/generate_qr')
def generate_qr():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    test_url = url_for('start_test', token=user.user_uuid, _external=True)


    qr = qrcode.make(test_url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')


# ==================== VISION TEST ROUTES ====================
@app.route('/start-test')
def start_test():
    token = request.args.get('token')
    if 'user_id' not in session:
        if token:
            user = User.query.filter_by(user_uuid=token).first()
            if user:
                session['user_id'] = user.id
            else:
                return "Invalid token", 403
        else:
            return redirect('/login')
    
    # >>> Reset finished test if scanning again <<<
    if token in finished_tests:
        del finished_tests[token]

    return render_template("start_test.html")


@app.route('/vision_test')
def vision_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('test.html')


@app.route('/submit_score', methods=['POST'])
def submit_score():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 403

    data = request.get_json()
    result = VisionTestResult(
        user_id=session['user_id'],
        right_eye_score=data['right_eye'],
        left_eye_score=data['left_eye']
    )
    db.session.add(result)
    db.session.commit()

    # Mark test as finished for controller
    token = User.query.get(session['user_id']).user_uuid
    finished_tests[token] = {
        'right_eye': data['right_eye'],
        'left_eye': data['left_eye']
    }

    right_acuity = calculate_visual_acuity(data['right_eye'])
    left_acuity = calculate_visual_acuity(data['left_eye'])

    return jsonify({
        'message': 'Result saved',
        'right_eye_score': data['right_eye'],
        'left_eye_score': data['left_eye'],
        'right_eye_acuity': right_acuity,
        'left_eye_acuity': left_acuity
    })

@app.route('/check_finished/<token>')
def check_finished(token):
    if token in finished_tests:
        return jsonify({
            'finished': True,
            'right_eye': finished_tests[token]['right_eye'],
            'left_eye': finished_tests[token]['left_eye']
        })
    return jsonify({'finished': False})


@app.route('/my_results', methods=['GET'])
def my_results():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    results = VisionTestResult.query.filter_by(user_id=session['user_id']).order_by(VisionTestResult.timestamp.desc()).all()
    return jsonify([
        {
            'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M'),
            'right_eye_score': r.right_eye_score,
            'left_eye_score': r.left_eye_score
        } for r in results
    ])


# ==================== DUAL DEVICE SYNC ROUTES ====================
@app.route('/controller')
def controller():
    token = request.args.get('token')
    return render_template("controller.html", token=token)

@app.route('/test-display')
def test_display():
    token = request.args.get('token')
    return render_template("test_display.html", token=token)

@app.route('/mark_ready/<token>', methods=['POST'])
def mark_ready(token):
    session_ready[token] = True
    return jsonify({'status': 'ready'})

@app.route('/check_ready/<token>')
def check_ready(token):
    return jsonify({'ready': session_ready.get(token, False)})

@app.route('/submit_direction', methods=['POST'])
def submit_direction():
    data = request.get_json()
    token = data.get('token')
    direction = data.get('direction')
    latest_directions[token] = direction
    return jsonify({'status': 'received'})

@app.route('/get_direction')
def get_direction():
    token = request.args.get('token')
    direction = latest_directions.get(token)
    latest_directions[token] = None
    return jsonify({'direction': direction})

# ==================== VISUAL ACUITY CALCULATION ====================
def calculate_visual_acuity(score, max_score=8):
    acuity_scale = {
        8: "20/20",
        7: "20/25",
        6: "20/30",
        5: "20/40",
        4: "20/50",
        3: "20/60",
        2: "20/80",
        1: "20/100",
        0: "worse than 20/100"
    }
    return acuity_scale.get(score, "Unknown")


# ==================== RUN ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5050, debug=True)



