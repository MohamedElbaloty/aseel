"""
Post Check-in System - Flask Backend API
"""
import json, os, sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

sys.path.insert(0, os.path.dirname(__file__))
from db.database import (
    initialize_db, save_checkin, get_all_checkins,
    get_employee_checkins, get_stats, get_employees,
    delete_checkin, delete_employee_visits, delete_all_visits
)
from ai.extractor import extract_checkin_data, transcribe_audio

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# ─── Simple in-memory auth (replace with DB auth in production) ─────────────
USERS = {
    "admin":    {"password": "admin123",  "role": "admin",    "name": "مدير النظام"},
    "emp001":   {"password": "pass123",   "role": "employee", "name": "أحمد المنصوري"},
    "emp002":   {"password": "pass123",   "role": "employee", "name": "سارة الزهراني"},
    "emp003":   {"password": "pass123",   "role": "employee", "name": "خالد العمري"},
}

# ─── Serve Frontend ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('../frontend', path)

# ─── Auth ─────────────────────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    user = USERS.get(username)
    if not user or user['password'] != password:
        return jsonify({'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401
    return jsonify({
        'username': username,
        'name': user['name'],
        'role': user['role'],
        'token': f"{username}:{user['role']}"  # simplified token
    })

# ─── AI Extract ──────────────────────────────────────────────────────────────
@app.route('/api/extract', methods=['POST'])
def extract():
    data = request.json or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'الرسالة فارغة'}), 400
    try:
        extracted = extract_checkin_data(message)
        return jsonify({'data': extracted})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'لم يتم العثور على ملف صوتي'}), 400
    file = request.files['audio']
    if file.filename == '':
        return jsonify({'error': 'ملف فارغ'}), 400
    
    import tempfile
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp_path = tmp.name
        file.save(tmp_path)
        
        text = transcribe_audio(tmp_path)
        os.remove(tmp_path)
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─── Check-ins ────────────────────────────────────────────────────────────────
@app.route('/api/checkins', methods=['POST'])
def create_checkin():
    payload = request.json or {}
    data = payload.get('data', {})
    employee_id = payload.get('employee_id', 'unknown')
    employee_name = payload.get('employee_name', 'Unknown')
    raw_message = payload.get('raw_message', '')
    record_id = save_checkin(data, employee_id, employee_name, raw_message)
    return jsonify({'success': True, 'id': record_id})

@app.route('/api/checkins', methods=['GET'])
def list_checkins():
    limit = int(request.args.get('limit', 200))
    records = get_all_checkins(limit)
    return jsonify({'records': records, 'total': len(records)})

@app.route('/api/checkins/me', methods=['GET'])
def my_checkins():
    employee_id = request.args.get('employee_id', '')
    limit = int(request.args.get('limit', 10))
    records = get_employee_checkins(employee_id, limit)
    return jsonify({'records': records})

@app.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(get_stats())

@app.route('/api/employees', methods=['GET'])
def employees():
    return jsonify(get_employees())

@app.route('/api/checkins/<int:record_id>', methods=['DELETE'])
def delete_checkin_api(record_id):
    data = request.json or {}
    employee_id = data.get('employee_id', '')
    role = data.get('role', 'employee')
    success = delete_checkin(record_id, employee_id, role)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'لم يتم العثور على السجل أو لا تملك صلاحية الحذف'}), 403

@app.route('/api/checkins/employee/<emp_id>', methods=['DELETE'])
def delete_employee_records(emp_id):
    data = request.json or {}
    if data.get('role') != 'admin':
        return jsonify({'error': 'غير مصرح'}), 403
    count = delete_employee_visits(emp_id)
    return jsonify({'success': True, 'deleted': count})

@app.route('/api/checkins/all', methods=['DELETE'])
def delete_all_records():
    data = request.json or {}
    if data.get('role') != 'admin':
        return jsonify({'error': 'غير مصرح'}), 403
    count = delete_all_visits()
    return jsonify({'success': True, 'deleted': count})

if __name__ == '__main__':
    initialize_db()
    port = int(os.getenv('PORT', 5050))
    is_prod = os.getenv('RAILWAY_ENVIRONMENT') is not None
    print(f'🚀 Server running at http://localhost:{port}')
    app.run(host='0.0.0.0', port=port, debug=not is_prod)

