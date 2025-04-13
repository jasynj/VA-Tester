from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(100))
    result = db.Column(db.String(50))

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
    test_url = url_for('start_test', _external=True)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Regenerate the database schema with new fields
    app.run(debug=True)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')



"""
from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vision_test.db'
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

# ==================== MODELS ====================
# Data base
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    user_uuid = db.Column(db.String(36), unique=True, nullable=False)

class VisionTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(100))
    result = db.Column(db.String(50))

# ==================== ROUTES ====================
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data['email']
    password = data['password']
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 409
    user = User(email=email,
                password_hash=generate_password_hash(password),
                user_uuid=str(uuid.uuid4()))
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Signup successful'})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data['email']
    password = data['password']
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user_id'] = user.id
    return jsonify({'message': 'Login successful'})

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    """
