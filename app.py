from flask import Flask, jsonify

# Initialize Flask app FIRST
app = Flask(__name__)

# Then define routes
@app.route('/')
def home():
    return jsonify({
        "message": "Office Assistant API",
        "endpoints": {
            "login": "POST /login",
            "ask": "POST /ask (requires auth)",
            "health": "GET /health"
        }
    })

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

# Must be at the bottom
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)