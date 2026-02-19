from faster_whisper import WhisperModel
import io
import os

class FasterTranscriber:
    def __init__(self, model_size="medium", compute_type="int8"):
        """
        Initializes the faster-whisper model.
        Args:
            model_size (str): "tiny", "base", "small", "medium", "large-v3".
            compute_type (str): "int8", "float16", "float32". 
                                "int8" is best for CPU inference. 
                                "float16" for GPU if available.
        """
        
        # Check if we have CUDA, else use CPU
        # Note: accurate detection of available providers depends on onnxruntime build.
        # For simplicity in this desktop app, we'll default to CPU/int8 for maximum compatibility unless specified.
        # User can modify this for GPU.
        
        backend = "cpu"
        # Simple CUDA check via environment variables or library availability could be added here.
        
        print(f"Loading faster-whisper model '{model_size}' on {backend}...", flush=True)
        self.model = WhisperModel(model_size, device=backend, compute_type=compute_type)
        print("Model loaded.", flush=True)

    def transcribe(self, audio_data):
        """
        Transcribes audio data (bytes).
        Args:
            audio_data (BytesIO): WAV audio buffer.
        Returns:
            str: Transcribed text.
        """
        if not audio_data:
            return ""
        
        # faster-whisper handles file-like objects
        segments, info = self.model.transcribe(audio_data, beam_size=5, language="he")
        
        text = ""
        for segment in segments:
            text += segment.text
        
        return text.strip()

if __name__ == "__main__":
    # Test (requires a sample file or mock)
    print("Transcriber initialized.")
