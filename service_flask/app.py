import os
import jwt  # PyJWT library
from flask import Flask, jsonify, request
from functools import wraps
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
SHARED_SECRET_KEY = os.environ.get('SHARED_SECRET_KEY')

if not SHARED_SECRET_KEY:
    raise ValueError("No SHARED_SECRET_KEY set in .env file")

# --- Authentication Decorator ---

def token_required(f):
    """
    A decorator to validate the JWT token from the Authorization header.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split()

            # Check for 'Bearer <token>' format
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
            else:
                return jsonify({"message": "Invalid Authorization header format"}), 401

        if not token:
            return jsonify({"message": "Token is missing"}), 401

        # --- Token Validation ---
        try:
            # Decode the token using the shared secret
            # This verifies the signature and expiration (if any)
            data = jwt.decode(token, SHARED_SECRET_KEY, algorithms=["HS256"])
            # Pass the decoded payload (e.g., user info) to the route
            kwargs['token_payload'] = data
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid"}), 403 # 403 Forbidden

        return f(*args, **kwargs)
    return decorated

# --- API Endpoints ---

@app.route("/")
def home():
    """A simple check to see if the service is online."""
    return jsonify({"status": "Flask Service is running!"})


@app.route("/api/v1/get-data")
@token_required  # Protect this route with the decorator
def get_data(token_payload):
    """
    This is our secure endpoint. It only runs if @token_required succeeds.
    'token_payload' is passed in from the decorator.
    """
    
    # Can now trust the data in the payload
    user_id = token_payload.get('user_id')

    # For this prototype, just send back a success message.
    response_data = {
        "status": "success",
        "data_from_flask": "This is your secure, specialized data.",
        "user_id_seen": user_id
    }
    
    return jsonify(response_data), 200

@app.route("/api/v1/validate-student", methods=['POST'])
@token_required 
def validate_student(token_payload):
    """
    This endpoint receives student data from Django and performs 
    complex/specialized validation.
    """
    
    # 1. The @token_required decorator ensures the request is trusted.
    # 2. Can get the data Django sent via the request body:
    student_data = request.get_json()
    
    # --- PROTOTYPE VALIDATION LOGIC ---
    # In a real app, run complex checks here (e.g., check for 
    # profanity, verify an external license key, cross-reference against
    # another database).
    
    # For this test, we'll check if the student ID is "123" and force a failure.
    if student_data.get('student_id') == '123':
        return jsonify({
            "validation_ok": False,
            "error": "Student ID '123' is reserved for administration."
        }), 200
    
    # If all checks pass, return success
    return jsonify({
        "validation_ok": True,
        "message": "Student data passed all external validation checks."
    }), 200

@app.route("/api/v1/predict-risk", methods=['POST'])
@token_required
def predict_risk(token_payload):
    """
    ML Endpoint: Predicts student dropout risk based on financial and academic data.
    """
    data = request.get_json()
    
    # 1. Extract features for the model
    # In a real app, these would be inputs to a loaded .pkl model
    balance = float(data.get('current_balance', 0))
    course_count = int(data.get('course_count', 0))
    
    # 2. Apply Logic (Simulated ML Model)
    # Rule: If they owe > $500 OR have 0 courses, they are high risk.
    risk_score = 0
    risk_label = "Low Risk"
    
    if balance > 500:
        risk_score += 50
    if balance > 1000:
        risk_score += 30
        
    if course_count == 0:
        risk_score += 40
    elif course_count < 2:
        risk_score += 10
        
    # Cap score at 100
    risk_score = min(risk_score, 100)
    
    if risk_score > 75:
        risk_label = "Critical"
    elif risk_score > 40:
        risk_label = "Moderate Risk"
        
    return jsonify({
        "status": "success",
        "student_id": data.get('student_id'),
        "prediction": {
            "risk_score": risk_score,
            "label": risk_label
        }
    })

# --- Run the App ---

if __name__ == '__main__':
    # Run on port 5001 to avoid conflicting with Django
    app.run(debug=True, port=5001)