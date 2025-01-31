import speech_recognition as sr
import numpy as np
from typing import Optional, Union
import io
import wave

class AudioTranscriber:
    """
    A class to handle speech-to-text transcription using various input methods.
    Supports direct microphone input, audio file transcription, and raw audio data transcription.
    Uses Google's Speech Recognition service for accurate transcription.
    """

    def __init__(self):
        """
        Initialize the transcriber with optimal settings for medical transcription.
        Sets up the speech recognizer and configures sensitivity parameters.
        Automatically detects and configures the MacBook Pro's microphone.
        """
        # Initialize the speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Configure recognition sensitivity settings
        self.recognizer.energy_threshold = 100      # Lower values make it more sensitive to quiet speech
        self.recognizer.dynamic_energy_threshold = True  # Automatically adjust for ambient noise
        self.recognizer.pause_threshold = 2.0       # Wait 2 seconds of silence before considering the phrase complete
        
        # Attempt to find and configure the MacBook Pro's built-in microphone
        mics = sr.Microphone.list_microphone_names()
        self.device_index = None
        for index, name in enumerate(mics):
            if "macbook pro microphone" in name.lower():
                self.device_index = index
                break

    def transcribe_audio_data(self, audio_data: np.ndarray, sample_rate: int = 44100) -> Optional[str]:
        """
        Convert raw audio data (numpy array) into text using speech recognition.
        
        Process:
        1. Converts numpy array to WAV format in memory
        2. Creates an AudioFile object from the WAV data
        3. Performs speech recognition on the audio
        
        Args:
            audio_data: Raw audio data as a numpy array
            sample_rate: Audio sampling rate in Hz (default: 44100)
            
        Returns:
            Transcribed text if successful, None if transcription fails
        """
        # Step 1: Create an in-memory WAV file
        byte_io = io.BytesIO()
        with wave.open(byte_io, 'wb') as wav_file:
            wav_file.setnchannels(1)              # Mono audio
            wav_file.setsampwidth(2)              # 2 bytes per sample (16-bit audio)
            wav_file.setframerate(sample_rate)    # Set the sample rate
            wav_file.writeframes(audio_data.tobytes())
        
        # Step 2: Create AudioData object from the WAV file
        byte_io.seek(0)  # Reset buffer position to start
        with sr.AudioFile(byte_io) as source:
            audio = self.recognizer.record(source)
        
        # Step 3: Attempt transcription
        try:
            text = self.recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            print("Speech recognition could not understand the audio")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from speech recognition service; {e}")
            return None

    def transcribe_file(self, audio_file: str) -> Optional[str]:
        """
        Transcribe audio from a WAV file to text.
        
        Args:
            audio_file: Path to the WAV file to transcribe
            
        Returns:
            Transcribed text if successful, None if transcription fails
            
        Note:
            The file should be a WAV file with proper formatting.
            Handles errors that might occur during file reading or transcription.
        """
        try:
            with sr.AudioFile(audio_file) as source:
                # Record the entire file into an AudioData object
                audio = self.recognizer.record(source)
                # Perform the transcription
                text = self.recognizer.recognize_google(audio)
                return text
        except Exception as e:
            print(f"Error transcribing audio file: {e}")
            return None

    def transcribe_microphone(self, timeout: Optional[Union[float, int]] = None) -> Optional[str]:
        """
        Record and transcribe audio directly from the microphone.
        
        Process:
        1. Opens microphone stream
        2. Adjusts for ambient noise
        3. Listens for speech
        4. Transcribes the recorded audio
        
        Args:
            timeout: Maximum time to listen for speech (in seconds)
                    None means listen indefinitely
            
        Returns:
            Transcribed text if successful, None if transcription fails
            
        Note:
            Uses the MacBook Pro's microphone if found, otherwise falls back to default microphone.
            Automatically adjusts for background noise before recording.
        """
        # Select appropriate microphone (MacBook Pro or default)
        mic = sr.Microphone(device_index=self.device_index) if self.device_index is not None else sr.Microphone()
        
        with mic as source:
            try:
                # Step 1: Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Listening...")
                
                # Step 2: Listen for speech
                audio = self.recognizer.listen(source, timeout=timeout)
                
                # Step 3: Perform transcription
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.WaitTimeoutError:
                print("Listening timed out")
                return None
            except sr.UnknownValueError:
                print("Speech recognition could not understand the audio")
                return None
            except sr.RequestError as e:
                print(f"Could not request results from speech recognition service; {e}")
                return None 