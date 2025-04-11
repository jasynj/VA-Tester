from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vision_test.db'
db = SQLAlchemy(app)
CORS(app)

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
