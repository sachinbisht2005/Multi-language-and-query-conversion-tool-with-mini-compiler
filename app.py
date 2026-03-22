from flask import Flask, request, jsonify
from flask_cors import CORS
from transpiler.engine import transpile

app = Flask(__name__)
CORS(app)

@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    source_code = data.get('source_code', '').strip()
    source_lang = data.get('source_lang', '').lower()
    target_lang = data.get('target_lang', '').lower()

    if not source_code:
        return jsonify({"error": "source_code is required"}), 400
    if not source_lang:
        return jsonify({"error": "source_lang is required"}), 400
    if not target_lang:
        return jsonify({"error": "target_lang is required"}), 400

    supported = ['c', 'python', 'cpp']
    if source_lang not in supported:
        return jsonify({"error": f"Unsupported source language: {source_lang}"}), 400
    if target_lang not in supported:
        return jsonify({"error": f"Unsupported target language: {target_lang}"}), 400
    if source_lang == target_lang:
        return jsonify({"converted_code": source_code, "message": "Same language, no conversion needed"})

    try:
        result = transpile(source_code, source_lang, target_lang)
        return jsonify({"converted_code": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "Transpiler API is running"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
