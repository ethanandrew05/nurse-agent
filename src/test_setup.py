from audio.recorder import AudioRecorder
from audio.transcriber import AudioTranscriber
import spacy
import time

def test_audio_and_transcription():
    print("Testing audio recording and transcription...")
    
    # Initialize components
    recorder = AudioRecorder()
    transcriber = AudioTranscriber()
    
    try:
        # Test recording
        print("\nStarting 5-second recording...")
        recorder.start_recording()
        time.sleep(5)  # Record for 5 seconds
        print("Stopping recording...")
        audio_data = recorder.stop_recording()
        
        # Save the recording
        recorder.save_to_wav("test_recording.wav")
        print("Recording saved to test_recording.wav")
        
        # Test transcription
        print("\nTranscribing recorded audio...")
        text = transcriber.transcribe_audio_data(audio_data)
        if text:
            print(f"Transcription: {text}")
        else:
            print("Transcription failed")
            
    except Exception as e:
        print(f"Error during audio test: {e}")

def test_nlp():
    print("\nTesting NLP functionality...")
    
    try:
        # Load the spaCy model
        nlp = spacy.load("en_core_web_trf")
        
        # Test text
        test_text = "The patient complained of severe headache and nausea. Dr. Smith prescribed 500mg of acetaminophen."
        
        # Process the text
        doc = nlp(test_text)
        
        # Print entities
        print("\nDetected entities:")
        for ent in doc.ents:
            print(f"- {ent.text} ({ent.label_})")
            
        # Print sentence segmentation
        print("\nSentences:")
        for sent in doc.sents:
            print(f"- {sent.text}")
            
    except Exception as e:
        print(f"Error during NLP test: {e}")

if __name__ == "__main__":
    print("Running setup tests...\n")
    test_audio_and_transcription()
    test_nlp()
    print("\nTests completed.") 