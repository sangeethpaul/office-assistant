from flask import Flask, request, jsonify, render_template
from PyPDF2 import PdfReader
import google.generativeai as genai
import os
from pathlib import Path

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-pro-latest')


def load_knowledge():
    """Load all knowledge files"""
    knowledge = ""
    knowledge_dir = Path('knowledge')

    for file in knowledge_dir.glob('*'):
        try:
            if file.suffix == '.pdf':
                knowledge += f"\n[PDF: {file.name}]\n{PdfReader(file).pages[0].extract_text()[:1000]}"
            elif file.suffix in ('.md', '.txt'):
                knowledge += f"\n[Text: {file.name}]\n{file.read_text()[:1000]}"
            elif file.suffix == '.csv':
                knowledge += f"\n[CSV: {file.name}]\n{file.read_text()[:1000]}"
        except Exception as e:
            print(f"Error loading {file}: {str(e)}")

    return knowledge


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask():
    try:
        query = request.json.get('query', '')
        knowledge = load_knowledge()

        response = model.generate_content(
            f"""Answer this query using ONLY the following information:
            {knowledge}

            Query: {query}

            Rules:
            1. Be concise
            2. If unsure, say "I couldn't find that in our documents"
            3. Never make up information"""
        )

        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Create required directories
    os.makedirs('knowledge', exist_ok=True)

    # Manual .env loading if needed
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    # Verify Gemini API key is set
    if not os.getenv("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY not found in environment variables")

    app.run(host='0.0.0.0', port=5000)