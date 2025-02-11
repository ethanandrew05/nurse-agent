from recorder import AudioRecorder
from transcriber import AudioTranscriber
import time
import os
import speech_recognition as sr
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import json
from create_database import create_database, update_record, get_patient_record, list_patients
import threading
import sys
import select
import signal

# Get the absolute path to the database
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(SCRIPT_DIR, 'medical_records.db')

# Load environment variables from .env file
load_dotenv()

# Define all possible database fields
DB_FIELDS = [
    "symptoms",
    "vital_signs",
    "medications",
    "allergies",
    "medical_history",
    "family_history",
    "diagnosis",
    "treatment_plan",
    "follow_up_date",
    "notes"
]

# Global flag for recording state
is_recording = True

def signal_handler(signum, frame):
    """Handle the stop signal from the web app"""
    global is_recording
    is_recording = False
    print("\nStop signal received, finishing recording...")

def analyze_with_groq(text: str, api_key: str) -> dict:
    """
    Analyze transcribed text using Groq's LLaMA model and structure it for database input.
    Preserves existing data and only updates allowed fields.
    
    Args:
        text: The transcribed text to analyze
        api_key: Groq API key
    """
    client = Groq(api_key=api_key)
    
    # Construct the prompt
    field_list = "\n".join([f"- {field}: (null if not mentioned)" for field in DB_FIELDS])
    prompt = f"""You are a medical data extraction assistant. Your task is to extract medical information from the conversation and format it as a valid JSON object.

Required fields to extract:
{field_list}

Guidelines:
1. Extract both explicit and implicit information
2. Convert relative dates to actual dates
3. Include all mentioned symptoms
4. Include past conditions in medical history
5. Use null for missing information
6. Format numbers as integers where appropriate
7. Keep text fields as simple strings
8. Ensure the output is valid JSON
9. DO NOT extract or modify patient name, age, gender, or date of birth

Example output format:
{{
    "symptoms": "chest pain, shortness of breath",
    "vital_signs": "BP 140/90",
    "medications": "aspirin",
    "allergies": null,
    "medical_history": "hypertension",
    "family_history": null,
    "diagnosis": "angina",
    "treatment_plan": "prescribed nitroglycerin",
    "follow_up_date": "2024-02-15",
    "notes": "Patient exercises regularly"
}}

Analyze this transcript and provide only a JSON object with the extracted information:
{text}"""

    # Call Groq API
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.5,  # Lower temperature for more consistent output
    )
    
    # Parse the response as JSON
    try:
        response_text = chat_completion.choices[0].message.content
        # Try to find JSON object in the response
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
        else:
            print("Error: No JSON object found in response")
            return {}
    except json.JSONDecodeError:
        print("Error: Could not parse Groq response as JSON")
        print("Response was:", response_text)
        return {}

def check_for_enter():
    """Check if Enter was pressed"""
    while True:
        if select.select([sys.stdin], [], [], 0.1)[0]:  # 0.1 second timeout
            sys.stdin.readline()
            return True
    return False

def main():
    """
    Main function to demonstrate the speech recognition capabilities.
    Recording stops after silence duration or when stop signal received.
    """
    
    # Set up signal handler
    signal.signal(signal.SIGUSR1, signal_handler)
    
    # Get Groq API key from environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Please set your GROQ_API_KEY environment variable")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Make sure database exists
    print(f"Using database at: {DATABASE_PATH}")  # Debug print
    create_database()
    
    # Get patient ID from command line argument
    if len(sys.argv) != 2:
        print("Usage: python example.py <patient_id>")
        return
        
    try:
        patient_id = int(sys.argv[1])
        print(f"Looking for patient ID: {patient_id}")  # Debug print
        patient = get_patient_record(patient_id)
        if not patient:
            print("Patient not found in database.")
            return
        
        full_name = f"{patient['first_name'] or ''} {patient['last_name'] or ''}".strip()
        print(f"\nUpdating record for patient: {full_name or 'Name not specified'}")
    except ValueError:
        print("Invalid patient ID")
        return

    # Initialize recorder and transcriber
    recorder = AudioRecorder()
    transcriber = AudioTranscriber()
    
    try:
        print("\nStarting recording session...")
        print("Adjusting for ambient noise... (please be quiet)")
        
        # Generate timestamp for file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_filename = f"output/transcription_{timestamp}.txt"
        analysis_filename = f"output/analysis_{timestamp}.json"
        
        # Record audio until silence or stop signal
        with sr.Microphone() as source:
            print("\nListening... (Press stop button or wait for silence)")
            transcriber.recognizer.adjust_for_ambient_noise(source)
            
            # Configure transcriber sensitivity settings
            transcriber.recognizer.energy_threshold = 300    # Moderate sensitivity
            transcriber.recognizer.dynamic_energy_threshold = True   # Enable auto-adjust
            transcriber.recognizer.pause_threshold = 1.5     # Stop after 1.5 seconds of silence
            transcriber.recognizer.phrase_threshold = 0.3    # Shorter minimum speaking time
            transcriber.recognizer.non_speaking_duration = 0.8  # Shorter silence detection
            
            try:
                # Listen with timeout to check is_recording flag
                while is_recording:
                    try:
                        audio = transcriber.recognizer.listen(source, timeout=1)
                        if audio:
                            break
                    except sr.WaitTimeoutError:
                        continue
                
                if audio:
                    # Convert audio to text
                    text = transcriber.recognizer.recognize_google(audio)
                    print("\nTranscription:")
                    print(text)
                    
                    # Analyze with Groq
                    print("\nAnalyzing transcription with Groq...")
                    analysis = analyze_with_groq(text, api_key)
                    print("\nExtracted Information:")
                    print(json.dumps(analysis, indent=2))
                    
                    # Update database
                    print("\nUpdating database...")
                    update_record(patient_id, analysis)
                    
                    # Save transcription and analysis to files
                    with open(text_filename, 'w') as f:
                        f.write(f"Transcription recorded at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write("-" * 50 + "\n\n")
                        f.write(text)
                    
                    with open(analysis_filename, 'w') as f:
                        json.dump({
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "transcription": text,
                            "extracted_information": analysis
                        }, f, indent=2)
                    
                    print(f"\nTranscription saved to: {text_filename}")
                    print(f"Analysis saved to: {analysis_filename}")
                    
                    # Display updated patient record
                    print("\nUpdated patient record:")
                    updated_patient = get_patient_record(patient_id)
                    for key, value in updated_patient.items():
                        if value is not None:
                            print(f"{key}: {value}")
                
            except sr.UnknownValueError:
                print("\nTranscription failed. Please try speaking louder and more clearly.")
            except sr.RequestError as e:
                print(f"\nCould not request results from speech recognition service; {e}")

    except KeyboardInterrupt:
        print("\nRecording interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("\nDone!")

if __name__ == "__main__":
    main() 