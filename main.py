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
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret')  # fallback is optional
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///vision_test.db')
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

# ==================== IN-MEMORY SYNC STATE ====================
session_ready = {}
latest_directions = defaultdict(lambda: None)

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
            "result": f"Right Eye: {r.right_eye_score}/8, Left Eye: {r.left_eye_score}/8"
        }
        for r in results
    ]

    # Optional: Recommend only based on latest result
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

    return render_template("dashboard.html", user=user, test_results=test_results, recommendations=recommendations)



@app.route('/generate_qr')
def generate_qr():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    test_url = f"http://11.28.7.179:5050/start-test?token={user.user_uuid}"

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
    return jsonify({'message': 'Result saved'})


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


# ==================== RUN ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5050, debug=True)




'''
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import qrcode
import io
import re

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vision_test.db'
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

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

# ==================== ROUTES ====================
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

        # Detect mobile vs desktop
        user_agent = request.headers.get('User-Agent', '')
        if is_mobile_device(user_agent):
            return jsonify({'message': 'Login successful', 'redirect': '/start-test'})
        else:
            return jsonify({'message': 'Login successful', 'redirect': '/dashboard'})

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    test_results = VisionTestResult.query.filter_by(user_id=user.id).order_by(VisionTestResult.timestamp.desc()).all()

    return render_template("dashboard.html", user=user, test_results=test_results)


@app.route('/generate_qr')
def generate_qr():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    test_url = f"http://11.28.7.179:5050/start-test?token={user.user_uuid}"

    qr = qrcode.make(test_url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)

    return send_file(buffer, mimetype='image/png')



@app.route('/start-test')
def start_test():
    token = request.args.get('token')

    if 'user_id' not in session:
        # If no session, try to login with token
        if token:
            user = User.query.filter_by(user_uuid=token).first()
            if user:
                session['user_id'] = user.id  # Auto-login
            else:
                return "Invalid token", 403
        else:
            return redirect('/login')

    return render_template("start_test.html")


@app.route('/controller')
def controller():
    token = request.args.get('token')
    return render_template("controller.html", token=token)

@app.route('/test-display')
def test_display():
    token = request.args.get('token')
    return render_template("test_display.html", token=token)


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
    return jsonify({'message': 'Result saved'})


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


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5050, debug=True)
'''


"""
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import qrcode
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vision_test.db'
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

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

# ==================== ROUTES ====================
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
        return jsonify({'message': 'Login successful', 'redirect': '/dashboard'})

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    test_results = VisionTestResult.query.filter_by(user_id=user.id).order_by(VisionTestResult.timestamp.desc()).all()

    return render_template("dashboard.html", user=user, test_results=test_results)


@app.route('/generate_qr')
def generate_qr():
    if 'user_id' not in session:
        return redirect('/login')

    test_url = url_for("start_test", _external=True)

    qr = qrcode.make(test_url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)

    return send_file(buffer, mimetype='image/png')


@app.route('/start-test')
def start_test():
    if 'user_id' not in session:
        return redirect('/login')
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
    return jsonify({'message': 'Result saved'})


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


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5050, debug=True)
"""


"""
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid
import qrcode
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vision_test.db'
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

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

# ==================== ROUTES ====================
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
        data = request.get_json()  # if using HTML form submit
        email = data['email']
        password = data['password']
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return render_template('login.html', error="Invalid credentials")

        session['user_id'] = user.id

    return jsonify({'message': 'Login successful', 'redirect': '/dashboard'})


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    test_results = VisionTestResult.query.filter_by(user_id=user.id).order_by(VisionTestResult.date.desc()).all()

    # Example recommendation logic
    recommendations = []
    for r in test_results:
        if "blurry" in r.result.lower():
            recommendations.append("Your vision seems blurry. Try reducing screen time and consider seeing an optometrist.")
        elif "mild" in r.result.lower():
            recommendations.append("Your eyes might be strained. Take regular breaks with the 20-20-20 rule.")
        elif "perfect" in r.result.lower():
            recommendations.append("Great vision! Keep up your healthy habits.")

    return render_template("dashboard.html", user=user, test_results=test_results, recommendations=recommendations)


@app.route('/generate_qr')
def generate_qr():
    if 'user_id' not in session:
        return redirect('/login')

    # Define the test URL (can be customized)
    test_url = url_for("start_test", _external=True)

    # Generate QR code image
    qr = qrcode.make(test_url)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)

    return send_file(buffer, mimetype='image/png')


@app.route('/start-test')
def start_test():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template("start_test.html")  # or however you're handling tests

@app.route('/vision_test')
def vision_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # optional, to restrict unauthenticated access
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
    return jsonify({'message': 'Result saved'})


@app.route('/save_result', methods=['POST'])
def save_result():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    result = VisionTestResult(
        user_id=session['user_id'],
        date=data['date'],
        result=data['result']
    )
    db.session.add(result)
    db.session.commit()
    return jsonify({'message': 'Result saved'})


@app.route('/my_results', methods=['GET'])
def my_results():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    results = VisionTestResult.query.filter_by(user_id=session['user_id']).all()
    return jsonify([{'date': r.date, 'result': r.result} for r in results])


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Regenerate the database schema with new fields
    app.run(host='0.0.0.0', port=5050, debug=True)
    #app.run(debug=True)

"""