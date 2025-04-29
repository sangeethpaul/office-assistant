import os
import glob
import json
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
import google.generativeai as genai

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

# Gemini Configuration
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest')


# Helper Functions
def load_users():
    """Load users from JSON file with error handling"""
    try:
        with open('auth/users.json') as f:
            return json.load(f)['users']
    except Exception as e:
        print(f"Error loading users: {str(e)}")
        return []


def get_allowed_files(user):
    """Get accessible files based on user permissions"""
    if user.get('admin'):
        return glob.glob('data/*')
    return [f"data/{fname}" for fname in user.get('access', [])]


# Authentication Middleware
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            token = token.split()[1]  # Remove "Bearer" prefix
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            request.current_user = next(
                u for u in load_users()
                if u['email'] == data['email']
            )
        except Exception as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401

        return f(*args, **kwargs)

    return decorated


# Routes
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = next(
            u for u in load_users()
            if u['email'] == data['email'] and
            bcrypt.checkpw(data['password'].encode(), u['password_hash'].encode())
        )
        token = jwt.encode({
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=8)
        }, app.config['SECRET_KEY'], algorithm="HS256")

        return jsonify({
            "token": token,
            "user": user['email'],
            "department": user['department']
        })
    except Exception as e:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route('/ask', methods=['POST'])
@token_required
def ask():
    try:
        user = request.current_user
        allowed_files = get_allowed_files(user)

        # Build knowledge context from allowed files
        knowledge = ""
        for file in allowed_files:
            if os.path.exists(file):
                if file.endswith('.pdf'):
                    knowledge += f"\n[PDF Content]: {PdfReader(file).pages[0].extract_text()[:1000]}..."
                elif file.endswith(('.md', '.txt')):
                    with open(file, 'r', encoding='utf-8') as f:
                        knowledge += f"\n[Text Content]: {f.read()[:1000]}..."

        response = model.generate_content(
            f"User from {user['department']} asks: {request.json.get('query')}\n"
            f"Answer ONLY using:\n{knowledge}\n"
            "If unsure, respond: 'This information is not available in your authorized documents.'"
        )

        return jsonify({
            "response": response.text,
            "department": user['department']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)