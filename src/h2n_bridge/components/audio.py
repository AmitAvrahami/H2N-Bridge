import sounddevice as sd
import numpy as np
import threading
import wave
import io
import queue

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_queue = queue.Queue()
        self.stream = None

    def start_recording(self):
        """Starts recording audio in a background thread."""
        if self.recording:
            return
        
        self.recording = True
        self.audio_queue = queue.Queue() # Clear queue
        
        def callback(indata, frames, time, status):
            if status:
                print(status, flush=True)
            self.audio_queue.put(indata.copy())

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=callback,
            dtype='int16' # Whisper usually expects standard formats, int16 is safe for saving to wav
        )
        self.stream.start()
        print("Recording started...", flush=True)

    def stop_recording(self):
        """Stops recording and returns the audio data as a bytes object (WAV format)."""
        if not self.recording:
            return None

        self.recording = False
        self.stream.stop()
        self.stream.close()
        print("Recording stopped.", flush=True)

        # Collect all chunks
        frames = []
        while not self.audio_queue.empty():
            frames.append(self.audio_queue.get())
        
        if not frames:
            return None

        # Concatenate all numpy arrays
        full_audio = np.concatenate(frames, axis=0)
        
        # Convert to WAV in-memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(full_audio.tobytes())
        
        wav_buffer.seek(0)
        return wav_buffer

if __name__ == "__main__":
    # Test recording
    import time
    recorder = AudioRecorder()
    recorder.start_recording()
    time.sleep(3)
    audio_data = recorder.stop_recording()
    print(f"Recorded {len(audio_data.getvalue())} bytes of audio.")
