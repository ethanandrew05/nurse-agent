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

# Load environment variables from .env file
load_dotenv()

# Define all possible database fields
DB_FIELDS = [
    "first_name",
    "last_name",
    "age",
    "gender",
    "date_of_birth",
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

def analyze_with_groq(text: str, api_key: str) -> dict:
    """
    Analyze transcribed text using Groq's LLaMA model and structure it for database input.
    
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

Example output format:
{{
    "patient_name": "John Smith",
    "age": 45,
    "gender": "Male",
    "date_of_birth": null,
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

def main():
    """
    Main function to demonstrate the speech recognition capabilities.
    Performs two separate transcription tests with detailed feedback.
    """
    
    # Get Groq API key from environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Please set your GROQ_API_KEY environment variable")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Make sure database exists
    create_database()
    
    # Get patient ID
    while True:
        try:
            patient_id = int(input("\nEnter patient ID (or 0 to exit): "))
            if patient_id == 0:
                return
            
            # Check if patient exists
            patient = get_patient_record(patient_id)
            if patient:
                full_name = f"{patient['first_name'] or ''} {patient['last_name'] or ''}".strip()
                print(f"\nUpdating record for patient: {full_name or 'Name not specified'}")
                break
            else:
                print("Patient not found. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

    # Initialize recorder and transcriber
    recorder = AudioRecorder()
    transcriber = AudioTranscriber()
    
    # Configure transcriber sensitivity settings
    transcriber.recognizer.energy_threshold = 300    # Moderate sensitivity
    transcriber.recognizer.dynamic_energy_threshold = True   # Enable auto-adjust
    transcriber.recognizer.pause_threshold = 1.5     # Stop after 1.5 seconds of silence
    transcriber.recognizer.phrase_threshold = 0.3    # Shorter minimum speaking time
    transcriber.recognizer.non_speaking_duration = 0.8  # Shorter silence detection
    
    try:
        # First Transcription Test
        print("\nTest 1: First transcription test")
        print("Speak when you see 'Listening...' (will stop after 1.5 seconds of silence)...")
        print("Adjusting for ambient noise... (please be quiet)")
        
        # Attempt first transcription without timeout
        text1 = transcriber.transcribe_microphone(timeout=None)
        
        # Display results of first test
        if text1:
            print("\nTranscription 1:")
            print(text1)
            
            # Analyze with Groq
            print("\nAnalyzing transcription with Groq...")
            analysis1 = analyze_with_groq(text1, api_key)
            print("\nExtracted Information 1:")
            print(json.dumps(analysis1, indent=2))
            
            # Update database
            print("\nUpdating database...")
            update_record(patient_id, analysis1)
            
        else:
            print("\nTranscription 1 failed. Please try speaking louder and more clearly.")
            
        # Brief pause between tests to reset
        time.sleep(1)
            
        # Second Transcription Test
        print("\nTest 2: Second transcription test")
        print("Speak when you see 'Listening...' (will stop after 1.5 seconds of silence)...")
        print("Adjusting for ambient noise... (please be quiet)")
        
        # Generate timestamp for file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_filename = f"output/transcription_{timestamp}.txt"
        analysis_filename = f"output/analysis_{timestamp}.json"
        
        # Record audio and get transcription
        with sr.Microphone() as source:
            print("\nListening...")
            transcriber.recognizer.adjust_for_ambient_noise(source)
            audio = transcriber.recognizer.listen(source)
            
            # Convert audio to text
            try:
                text2 = transcriber.recognizer.recognize_google(audio)
                print("\nTranscription 2:")
                print(text2)
                
                # Analyze with Groq
                print("\nAnalyzing transcription with Groq...")
                analysis2 = analyze_with_groq(text2, api_key)
                print("\nExtracted Information 2:")
                print(json.dumps(analysis2, indent=2))
                
                # Update database
                print("\nUpdating database...")
                update_record(patient_id, analysis2)
                
                # Save transcription and analysis to files
                with open(text_filename, 'w') as f:
                    f.write(f"Transcription recorded at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("-" * 50 + "\n\n")
                    f.write(text2)
                
                with open(analysis_filename, 'w') as f:
                    json.dump({
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "transcription": text2,
                        "extracted_information": analysis2
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
                print("\nTranscription 2 failed. Please try speaking louder and more clearly.")
            except sr.RequestError as e:
                print(f"\nCould not request results from speech recognition service; {e}")

    except KeyboardInterrupt:
        # Handle user interruption gracefully
        print("\nTranscription interrupted by user")
    except Exception as e:
        # Handle any other errors that might occur
        print(f"\nAn error occurred: {e}")
    finally:
        # Always indicate completion
        print("\nDone!")

if __name__ == "__main__":
    main() 