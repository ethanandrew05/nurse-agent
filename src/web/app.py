from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import subprocess
import signal
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variable to store the current recording process
recording_process = None

def get_patient_record(patient_id):
    """Get a patient record from the database."""
    conn = sqlite3.connect('../audio/medical_records.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM patient_records WHERE id = ?', (patient_id,))
    record = cursor.fetchone()
    
    if record:
        # Get column names
        columns = [description[0] for description in cursor.description]
        # Convert to dictionary
        result = dict(zip(columns, record))
    else:
        result = None
    
    conn.close()
    return result

def create_database():
    """Create the SQLite database with all necessary tables."""
    conn = sqlite3.connect('../audio/medical_records.db')
    cursor = conn.cursor()
    
    # Create the patients table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT,
        last_name TEXT,
        age INTEGER,
        gender TEXT,
        date_of_birth DATE,
        symptoms TEXT,
        vital_signs TEXT,
        medications TEXT,
        allergies TEXT,
        medical_history TEXT,
        family_history TEXT,
        diagnosis TEXT,
        treatment_plan TEXT,
        follow_up_date DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if we need to add a test patient
    cursor.execute("SELECT COUNT(*) FROM patient_records")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Add a test patient
        cursor.execute('''
        INSERT INTO patient_records (
            first_name, last_name, age, gender, date_of_birth,
            symptoms, vital_signs, medications, allergies,
            medical_history, family_history, diagnosis,
            treatment_plan, follow_up_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'John', 'Doe', 45, 'Male', '1979-01-15',
            'Headache, Fever', 'BP 120/80, Temp 38.5°C', 'Aspirin',
            'Penicillin', 'Hypertension', 'Father: Heart Disease',
            'Common Cold', 'Rest and fluids', '2024-02-15',
            'Patient reports feeling better'
        ))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/verify_patient', methods=['POST'])
def verify_patient():
    patient_id = request.form.get('patient_id')
    try:
        patient_id = int(patient_id)
        patient = get_patient_record(patient_id)
        if patient:
            return redirect(url_for('dashboard', patient_id=patient_id))
        else:
            return render_template('login.html', error="Patient not found")
    except ValueError:
        return render_template('login.html', error="Please enter a valid number")

@app.route('/dashboard/<int:patient_id>')
def dashboard(patient_id):
    patient = get_patient_record(patient_id)
    if patient:
        return render_template('dashboard.html', patient=patient)
    return redirect(url_for('index'))

@app.route('/manual_entry/<int:patient_id>')
def manual_entry(patient_id):
    patient = get_patient_record(patient_id)
    if patient:
        return render_template('manual_entry.html', patient=patient)
    return redirect(url_for('index'))

@app.route('/update_patient/<int:patient_id>', methods=['POST'])
def update_patient(patient_id):
    # Get all form data
    data = {
        'first_name': request.form.get('first_name'),
        'last_name': request.form.get('last_name'),
        'age': request.form.get('age'),
        'gender': request.form.get('gender'),
        'date_of_birth': request.form.get('date_of_birth'),
        'symptoms': request.form.get('symptoms'),
        'vital_signs': request.form.get('vital_signs'),
        'medications': request.form.get('medications'),
        'allergies': request.form.get('allergies'),
        'medical_history': request.form.get('medical_history'),
        'family_history': request.form.get('family_history'),
        'diagnosis': request.form.get('diagnosis'),
        'treatment_plan': request.form.get('treatment_plan'),
        'follow_up_date': request.form.get('follow_up_date'),
        'notes': request.form.get('notes')
    }
    
    # Remove empty fields
    data = {k: v for k, v in data.items() if v}
    
    # Update database
    conn = sqlite3.connect('../audio/medical_records.db')
    cursor = conn.cursor()
    
    if data:
        update_query = 'UPDATE patient_records SET ' + ', '.join(f'{k} = ?' for k in data.keys()) + ' WHERE id = ?'
        cursor.execute(update_query, list(data.values()) + [patient_id])
        conn.commit()
    
    conn.close()
    
    return redirect(url_for('dashboard', patient_id=patient_id))

@app.route('/start_recording/<int:patient_id>', methods=['POST'])
def start_recording(patient_id):
    global recording_process
    
    try:
        # Start example.py with the patient ID and show output in terminal
        recording_process = subprocess.Popen(
            ['python', '../audio/example.py', str(patient_id)],
            # Remove stdout and stderr capture to show in terminal
            bufsize=1,
            universal_newlines=True
        )
        
        return jsonify({"status": "success", "message": "Recording started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_process
    
    if recording_process:
        try:
            # Send SIGUSR1 signal to stop recording
            os.kill(recording_process.pid, signal.SIGUSR1)
            return jsonify({"status": "success", "message": "Stop signal sent"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "No recording in progress"}), 400

if __name__ == '__main__':
    create_database()
    app.run(host='0.0.0.0', port=8080, debug=True) 