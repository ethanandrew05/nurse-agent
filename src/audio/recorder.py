import pyaudio
import wave
import threading
import time
from typing import Optional
import numpy as np

class AudioRecorder:
    """
    A class to handle real-time audio recording from the microphone.
    Optimized for the MacBook Pro's built-in microphone.
    Uses PyAudio for low-level audio capture with callback-based recording.
    """

    def __init__(self, channels: int = 1, rate: int = 44100, chunk: int = 1024):
        """
        Initialize the audio recorder with specified parameters.
        
        Args:
            channels: Number of audio channels (1 for mono, 2 for stereo)
            rate: Sample rate in Hz (44100 is CD quality)
            chunk: Number of frames per buffer (affects latency and CPU usage)
            
        Note:
            Uses 32-bit float format for better audio quality.
            Automatically detects and configures the MacBook Pro's microphone.
        """
        # Audio configuration parameters
        self.channels = channels          # Number of audio channels
        self.rate = rate                  # Sample rate (Hz)
        self.chunk = chunk               # Buffer size
        self.format = pyaudio.paFloat32   # 32-bit float format for better quality
        
        # Initialize PyAudio system
        self.audio = pyaudio.PyAudio()
        
        # Recording state variables
        self.stream: Optional[pyaudio.Stream] = None
        self.frames = []                  # List to store audio frames
        self.is_recording = False         # Recording state flag

        # Find the MacBook Pro's built-in microphone
        self.device_index = None
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if "macbook pro microphone" in device_info["name"].lower():
                self.device_index = i
                break

    def start_recording(self):
        """
        Start recording audio from the microphone.
        
        Process:
        1. Initializes the audio stream with callback
        2. Starts the stream for continuous recording
        
        Note:
            Uses callback-based recording for better performance.
            Automatically uses the MacBook Pro's microphone if found.
        """
        if self.is_recording:
            return  # Prevent multiple recording sessions

        # Reset recording state
        self.frames = []
        self.is_recording = True
        
        # Configure and open the audio stream
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            input_device_index=self.device_index,
            stream_callback=self._callback
        )
        
        # Start the audio stream
        self.stream.start_stream()

    def _callback(self, in_data, frame_count, time_info, status):
        """
        Callback function for audio stream processing.
        
        Args:
            in_data: Recorded audio data
            frame_count: Number of frames in the buffer
            time_info: Timing information (unused)
            status: Stream status (unused)
            
        Returns:
            Tuple of (None, pyaudio.paContinue) to continue recording
        """
        self.frames.append(in_data)
        return (None, pyaudio.paContinue)

    def stop_recording(self) -> np.ndarray:
        """
        Stop recording and return the recorded audio data.
        
        Process:
        1. Stops the audio stream
        2. Closes the stream
        3. Converts recorded frames to numpy array
        
        Returns:
            Recorded audio as a numpy array (32-bit float format)
        """
        if not self.is_recording:
            return np.array([])

        # Stop recording
        self.is_recording = False
        
        # Clean up the audio stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        # Convert recorded frames to numpy array
        audio_data = np.frombuffer(b''.join(self.frames), dtype=np.float32)
        return audio_data

    def save_to_wav(self, filename: str):
        """
        Save the recorded audio to a WAV file.
        
        Args:
            filename: Path where the WAV file should be saved
            
        Note:
            Saves in the same format as recorded (channels, sample rate).
            Does nothing if no audio has been recorded.
        """
        if not self.frames:
            return

        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))

    def __del__(self):
        """
        Cleanup method to ensure proper resource release.
        Closes the audio stream and terminates PyAudio instance.
        """
        if self.stream:
            self.stream.close()
        if self.audio:
            self.audio.terminate() 