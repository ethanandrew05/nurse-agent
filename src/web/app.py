from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_cors import CORS
import sqlite3
from datetime import datetime
import subprocess
import signal
import os
import traceback  # Add this for better error tracking
import pdfkit
import tempfile

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global variable to store the current recording process
recording_process = None

def get_patient_record(patient_id):
    """Get a patient record from the database."""
    conn = sqlite3.connect('../audio/medical_records.db')
    cursor = conn.cursor()
    
    # Use the view that includes calculated age
    cursor.execute('SELECT * FROM patient_records_with_age WHERE id = ?', (patient_id,))
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

def get_patient_transcript(patient_id):
    """Get the latest transcript for a patient."""
    try:
        conn = sqlite3.connect('../audio/medical_records.db')
        cursor = conn.cursor()
        
        # First, check if the transcripts table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                transcript TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patient_records (id)
            )
        ''')
        conn.commit()
        
        cursor.execute('''
            SELECT transcript, timestamp 
            FROM transcripts 
            WHERE patient_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (patient_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"transcript": result[0], "timestamp": result[1]}
        return None
    except Exception as e:
        print(f"Error in get_patient_transcript: {e}")
        traceback.print_exc()
        return None

def generate_medical_report(patient_data, transcript_data):
    """Generate a comprehensive medical report."""
    try:
        if not patient_data:
            return "Error: Patient data not found"

        # Get current timestamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Start building the report
        report_sections = [
            f"MEDICAL REPORT",
            f"Generated on: {current_time}\n",
            
            "PATIENT INFORMATION",
            f"Name: {patient_data.get('first_name', 'N/A')} {patient_data.get('last_name', 'N/A')}",
            f"ID: {patient_data.get('id', 'N/A')}",
            f"Age: {patient_data.get('age', 'N/A')}",
            f"Date of Birth: {patient_data.get('date_of_birth', 'N/A')}",
            f"Gender: {patient_data.get('gender', 'N/A')}\n"
        ]
        
        # Add medical history if available
        if patient_data.get('medical_history'):
            report_sections.extend([
                "MEDICAL HISTORY",
                f"{patient_data.get('medical_history')}\n"
            ])
        
        # Add medications if available
        if patient_data.get('medications'):
            report_sections.extend([
                "CURRENT MEDICATIONS",
                f"{patient_data.get('medications')}\n"
            ])
        
        # Add allergies if available
        if patient_data.get('allergies'):
            report_sections.extend([
                "ALLERGIES",
                f"{patient_data.get('allergies')}\n"
            ])
        
        # Add vital signs if available
        if patient_data.get('vital_signs'):
            report_sections.extend([
                "VITAL SIGNS",
                f"{patient_data.get('vital_signs')}\n"
            ])
        
        # Add symptoms if available
        if patient_data.get('symptoms'):
            report_sections.extend([
                "CURRENT SYMPTOMS",
                f"{patient_data.get('symptoms')}\n"
            ])
        
        # Add diagnosis if available
        if patient_data.get('diagnosis'):
            report_sections.extend([
                "DIAGNOSIS",
                f"{patient_data.get('diagnosis')}\n"
            ])
        
        # Add treatment plan if available
        if patient_data.get('treatment_plan'):
            report_sections.extend([
                "TREATMENT PLAN",
                f"{patient_data.get('treatment_plan')}\n"
            ])

        # Add transcript analysis if available
        if transcript_data and transcript_data.get('transcript'):
            report_sections.extend([
                "VISIT TRANSCRIPT",
                f"Recorded on: {transcript_data.get('timestamp', 'Date not recorded')}",
                f"{transcript_data.get('transcript')}\n"
            ])

        # Add important notes if available
        if patient_data.get('notes'):
            report_sections.extend([
                "IMPORTANT NOTES",
                f"{patient_data.get('notes')}\n"
            ])

        # Add follow-up information if available
        if patient_data.get('follow_up_date'):
            report_sections.extend([
                "FOLLOW-UP",
                f"Next appointment: {patient_data.get('follow_up_date')}\n"
            ])

        # Join all sections with proper formatting
        return "\n".join(report_sections)
    except Exception as e:
        print(f"Error in generate_medical_report: {e}")
        traceback.print_exc()
        return f"Error generating report: {str(e)}"

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

@app.route('/check_recording_status')
def check_recording_status():
    global recording_process
    
    if recording_process:
        # Check if process is still running
        return_code = recording_process.poll()
        if return_code is None:
            # Process is still running
            return jsonify({"is_recording": True})
        else:
            # Process has ended
            recording_process = None
            return jsonify({"is_recording": False})
    else:
        return jsonify({"is_recording": False})

@app.route('/get_patient_data/<int:patient_id>')
def get_patient_data(patient_id):
    patient = get_patient_record(patient_id)
    if patient:
        return jsonify(patient)
    return jsonify({"error": "Patient not found"}), 404

@app.route('/create_new_patient', methods=['POST'])
def create_new_patient():
    conn = sqlite3.connect('../audio/medical_records.db')
    cursor = conn.cursor()
    
    try:
        # Insert a new blank patient record
        cursor.execute('''
        INSERT INTO patient_records (
            first_name, last_name, date_of_birth, gender,
            symptoms, vital_signs, medications, allergies,
            medical_history, family_history, diagnosis,
            treatment_plan, follow_up_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'New', 'Patient', None, None,
            None, None, None, None,
            None, None, None,
            None, None, 'New patient record created'
        ))
        
        # Get the ID of the newly created patient
        new_patient_id = cursor.lastrowid
        conn.commit()
        
        # Redirect to the dashboard for the new patient
        return redirect(url_for('dashboard', patient_id=new_patient_id))
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return render_template('login.html', error="Failed to create new patient")
    finally:
        conn.close()

@app.route('/summary_report/<int:patient_id>')
def summary_report(patient_id):
    patient = get_patient_record(patient_id)
    if patient:
        return render_template('summary_report.html', patient=patient)
    else:
        return "Patient not found", 404

@app.route('/generate_report/<int:patient_id>')
def generate_report(patient_id):
    """Generate a medical report for the specified patient."""
    try:
        # Get patient data
        patient_data = get_patient_record(patient_id)
        if not patient_data:
            print(f"Patient not found: {patient_id}")
            return jsonify({"error": "Patient not found"}), 404

        # Get transcript data
        transcript_data = get_patient_transcript(patient_id)
        print(f"Transcript data: {transcript_data}")
        
        # Generate the report
        report = generate_medical_report(patient_data, transcript_data)
        print(f"Report generated successfully for patient {patient_id}")
        
        return jsonify({"report": report})
    
    except Exception as e:
        print(f"Error generating report: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate report: {str(e)}"}), 500

def generate_report_html(patient_data, transcript_data):
    """Generate an HTML version of the medical report."""
    try:
        if not patient_data:
            return "Error: Patient data not found"

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create HTML report with styling
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 40px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #2980b9;
                    margin-top: 20px;
                }}
                .section {{
                    margin: 20px 0;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .timestamp {{
                    color: #7f8c8d;
                    font-size: 0.9em;
                    text-align: right;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MEDICAL REPORT</h1>
                <div class="timestamp">Generated on: {current_time}</div>
            </div>
            
            <div class="section">
                <h2>PATIENT INFORMATION</h2>
                <p>Name: {patient_data.get('first_name', 'N/A')} {patient_data.get('last_name', 'N/A')}</p>
                <p>ID: {patient_data.get('id', 'N/A')}</p>
                <p>Age: {patient_data.get('age', 'N/A')}</p>
                <p>Date of Birth: {patient_data.get('date_of_birth', 'N/A')}</p>
                <p>Gender: {patient_data.get('gender', 'N/A')}</p>
            </div>
        """
        
        if patient_data.get('medical_history'):
            html_content += f"""
            <div class="section">
                <h2>MEDICAL HISTORY</h2>
                <p>{patient_data.get('medical_history')}</p>
            </div>
            """
        
        if patient_data.get('medications'):
            html_content += f"""
            <div class="section">
                <h2>CURRENT MEDICATIONS</h2>
                <p>{patient_data.get('medications')}</p>
            </div>
            """
        
        if patient_data.get('allergies'):
            html_content += f"""
            <div class="section">
                <h2>ALLERGIES</h2>
                <p>{patient_data.get('allergies')}</p>
            </div>
            """
        
        if patient_data.get('vital_signs'):
            html_content += f"""
            <div class="section">
                <h2>VITAL SIGNS</h2>
                <p>{patient_data.get('vital_signs')}</p>
            </div>
            """
        
        if patient_data.get('symptoms'):
            html_content += f"""
            <div class="section">
                <h2>CURRENT SYMPTOMS</h2>
                <p>{patient_data.get('symptoms')}</p>
            </div>
            """
        
        if patient_data.get('diagnosis'):
            html_content += f"""
            <div class="section">
                <h2>DIAGNOSIS</h2>
                <p>{patient_data.get('diagnosis')}</p>
            </div>
            """
        
        if patient_data.get('treatment_plan'):
            html_content += f"""
            <div class="section">
                <h2>TREATMENT PLAN</h2>
                <p>{patient_data.get('treatment_plan')}</p>
            </div>
            """

        if transcript_data and transcript_data.get('transcript'):
            html_content += f"""
            <div class="section">
                <h2>VISIT TRANSCRIPT</h2>
                <p>Recorded on: {transcript_data.get('timestamp', 'Date not recorded')}</p>
                <p>{transcript_data.get('transcript')}</p>
            </div>
            """

        if patient_data.get('notes'):
            html_content += f"""
            <div class="section">
                <h2>IMPORTANT NOTES</h2>
                <p>{patient_data.get('notes')}</p>
            </div>
            """

        if patient_data.get('follow_up_date'):
            html_content += f"""
            <div class="section">
                <h2>FOLLOW-UP</h2>
                <p>Next appointment: {patient_data.get('follow_up_date')}</p>
            </div>
            """

        html_content += """
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        print(f"Error in generate_report_html: {e}")
        traceback.print_exc()
        return f"Error generating HTML report: {str(e)}"

@app.route('/download_report/<int:patient_id>')
def download_report(patient_id):
    """Generate and download a PDF version of the medical report."""
    try:
        # Get patient data
        patient_data = get_patient_record(patient_id)
        if not patient_data:
            return "Patient not found", 404

        # Get transcript data
        transcript_data = get_patient_transcript(patient_id)
        
        # Generate HTML report
        html_content = generate_report_html(patient_data, transcript_data)
        
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Configure PDF options
            options = {
                'page-size': 'Letter',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': 'UTF-8',
                'no-outline': None
            }
            
            # Convert HTML to PDF
            pdfkit.from_string(html_content, tmp.name, options=options)
            
            # Generate filename for download
            filename = f"medical_report_{patient_data['first_name']}_{patient_data['last_name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            return send_file(
                tmp.name,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
    
    except Exception as e:
        print(f"Error generating PDF: {e}")
        traceback.print_exc()
        return f"Error generating PDF: {str(e)}", 500

if __name__ == '__main__':
    create_database()
    app.run(host='0.0.0.0', port=8080, debug=True) 