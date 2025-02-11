import pyaudio
import wave
import numpy as np
import argparse
import signal
import sys
import time
import os
import sqlite3
from datetime import datetime
from create_database import transcribe_audio

class AudioRecorder:
    def __init__(self, patient_id, silence_duration=7, silence_threshold=500, max_chunk_size=1000000):
        self.patient_id = patient_id
        self.silence_duration = silence_duration  # seconds of silence before auto-stop
        self.silence_threshold = silence_threshold  # audio level threshold for silence
        self.max_chunk_size = max_chunk_size  # Maximum size of frames to hold in memory
        self.recording = False
        self.frames = []
        self.stream = None
        self.chunk_counter = 0
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # Create recordings directory if it doesn't exist
        self.recordings_dir = os.path.join(os.path.dirname(__file__), 'recordings')
        os.makedirs(self.recordings_dir, exist_ok=True)

        # Setup signal handlers for graceful shutdown
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except (AttributeError, ValueError) as e:
            print(f"Warning: Could not set up signal handlers: {e}")
    
    def _signal_handler(self, signum, frame):
        """Internal signal handler"""
        print(f"Received signal {signum}")
        self.stop_recording()

    def is_silent(self, data):
        """Check if the audio chunk is silent"""
        try:
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(np.square(audio_data)))
            return rms < self.silence_threshold
        except Exception as e:
            print(f"Error checking silence: {e}")
            return False

    def update_database(self, transcript):
        """Update the database with the transcribed text"""
        try:
            conn = sqlite3.connect('../audio/medical_records.db')
            cursor = conn.cursor()
            
            # Get current notes
            cursor.execute('SELECT notes FROM patient_records WHERE id = ?', (self.patient_id,))
            current_notes = cursor.fetchone()
            
            if current_notes:
                # Append new transcript to existing notes
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                updated_notes = f"{current_notes[0]}\n\n[{timestamp}]\n{transcript}" if current_notes[0] else f"[{timestamp}]\n{transcript}"
                
                # Update the database
                cursor.execute('''
                    UPDATE patient_records 
                    SET notes = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (updated_notes, self.patient_id))
                
                conn.commit()
                print("Database updated successfully")
            else:
                print("Patient record not found")
            
        except sqlite3.Error as e:
            print("Database error:", e)
        finally:
            if conn:
                conn.close()
    
    def write_frames_to_file(self, filename_prefix):
        """Write current frames to a temporary WAV file"""
        if not self.frames:
            return None
            
        temp_filename = f"{filename_prefix}_part_{self.chunk_counter}.wav"
        temp_path = os.path.join(self.recordings_dir, temp_filename)
        
        with wave.open(temp_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
        
        self.frames = []  # Clear frames from memory
        self.chunk_counter += 1
        return temp_path

    def combine_audio_files(self, temp_files, final_filename):
        """Combine multiple WAV files into a single file"""
        if not temp_files:
            return None
            
        with wave.open(temp_files[0], 'rb') as first_file:
            params = first_file.getparams()
            
        with wave.open(final_filename, 'wb') as output_file:
            output_file.setparams(params)
            
            for temp_file in temp_files:
                with wave.open(temp_file, 'rb') as wf:
                    output_file.writeframes(wf.readframes(wf.getnframes()))
                os.remove(temp_file)  # Clean up temp file
                
        return final_filename
    
    def record(self):
        """Start recording audio with silence detection and chunked file writing"""
        try:
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            print("* Recording started")
            self.recording = True
            silence_start = None
            temp_files = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"patient_{self.patient_id}_{timestamp}"
            
            while self.recording:
                try:
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)
                    
                    # Write to file if we've accumulated enough frames
                    if len(self.frames) * self.chunk >= self.max_chunk_size:
                        temp_file = self.write_frames_to_file(filename_prefix)
                        if temp_file:
                            temp_files.append(temp_file)
                    
                    # Check for silence
                    if self.is_silent(data):
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start >= self.silence_duration:
                            print("Detected {} seconds of silence, stopping recording".format(
                                self.silence_duration))
                            self.recording = False
                            break
                    else:
                        silence_start = None
                        
                except IOError as e:
                    print(f"IOError during recording: {e}")
                    break
                    
            # Write any remaining frames
            if self.frames:
                temp_file = self.write_frames_to_file(filename_prefix)
                if temp_file:
                    temp_files.append(temp_file)
            
            # Combine all temporary files
            final_filename = os.path.join(self.recordings_dir, f"{filename_prefix}_final.wav")
            final_path = self.combine_audio_files(temp_files, final_filename)
            
            if final_path:
                # Transcribe the final audio file and update database
                transcript = transcribe_audio(final_path)
                if transcript:
                    self.update_database(transcript)
                return final_path
            
        except Exception as e:
            print(f"Error during recording: {e}")
        finally:
            self.stop_recording()
    
    def stop_recording(self):
        """Stop recording and clean up resources"""
        print("Stopping recording...")
        
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.p:
                self.p.terminate()
                self.p = None
            
            self.recording = False
            
        except Exception as e:
            print(f"Error in stop_recording: {e}")

def main():
    parser = argparse.ArgumentParser(description='Record audio with silence detection')
    parser.add_argument('patient_id', type=int, help='Patient ID')
    parser.add_argument('--silence_duration', type=int, default=7,
                      help='Duration of silence (in seconds) before auto-stop')
    parser.add_argument('--silence_threshold', type=int, default=500,
                      help='Threshold for silence detection')
    
    args = parser.parse_args()
    
    recorder = AudioRecorder(
        args.patient_id,
        silence_duration=args.silence_duration,
        silence_threshold=args.silence_threshold
    )
    
    try:
        filename = recorder.record()
        if filename:
            print(f"* Recording saved to {filename}")
    except KeyboardInterrupt:
        print("\nRecording interrupted by user")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        if recorder:
            recorder.stop_recording()

if __name__ == "__main__":
    main() 