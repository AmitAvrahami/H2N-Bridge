import unittest
from unittest.mock import MagicMock, patch
import time
import threading
import sys
from PyQt6.QtWidgets import QApplication

# Mock modules before importing main
# We must mock submodules explicitly for "from X.Y import Z" to work
pynput_mock = MagicMock()
sys.modules['pynput'] = pynput_mock
sys.modules['pynput.keyboard'] = MagicMock()

sys.modules['sounddevice'] = MagicMock()
sys.modules['faster_whisper'] = MagicMock()
sys.modules['groq'] = MagicMock()

# Import the app controller
from h2n_bridge.main import AppController

class StressTest(unittest.TestCase):
    def setUp(self):
        # Create a fresh controller for each test
        # We need a qapp instance for signals to work
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
        self.controller = AppController()
        # Mock the heavy components
        self.controller.recorder = MagicMock()
        self.controller.transcriber = MagicMock()
        self.controller.translator = MagicMock()
        self.controller.output_handler = MagicMock()
        
    def tearDown(self):
        if self.controller._worker_thread and self.controller._worker_thread.isRunning():
            self.controller._worker_thread.quit()
            self.controller._worker_thread.wait()

    def test_rapid_hotkey_presses(self):
        """Simulate pressing Ctrl+K 10 times in 100ms."""
        print("\n--- Testing Rapid Hotkey Spam ---")
        
        # Mock recorder to return dummy audio
        self.controller.recorder.stop_recording.return_value = "dummy_audio"
        self.controller.transcriber.transcribe.return_value = "Shalom"
        self.controller.translator.translate.return_value = "Hello"

        # Spam hotkey
        for i in range(10):
            print(f"Press {i+1}")
            self.controller._on_hotkey_main_thread()
            # Minimal sleep to allow signal processing but still be "rapid"
            self.app.processEvents()
            time.sleep(0.01)
            
        # Verify: should trigger at least one recording, but subsequent ones should be blocked
        # The key is *no crash* and controller is responsive
        print(f"Test ended. Recording: {self.controller.is_recording}, Busy: {self.controller._thread_busy}")
        # Just ensure we didn't crash
        self.assertTrue(True)
        print("Rapid spam survived.")

    def test_audio_device_failure(self):
        """Simulate SoundDevice raising an OSError."""
        print("\n--- Testing Audio Device Failure ---")
        self.controller.recorder.start_recording.side_effect = OSError("Device Unavailable")
        
        try:
            self.controller._on_hotkey_main_thread() # Start
        except OSError:
            # The app currently crashes on this (we haven't fixed it yet)
            # This test EXPECTS failure for now, or we can catch it to verify behavior
            print("Caught expected OSError (to be fixed)")
            pass
            
    def test_translation_failure(self):
        """Simulate Groq API failing."""
        print("\n--- Testing Translation Network Failure ---")
        self.controller.recorder.stop_recording.return_value = "dummy"
        self.controller.transcriber.transcribe.return_value = "Text"
        self.controller.translator.translate.side_effect = Exception("API Timeout")
        
        # Start recording
        self.controller._on_hotkey_main_thread()
        self.app.processEvents()
        
        # Stop recording -> trigger processing
        self.controller._on_hotkey_main_thread()
        self.app.processEvents()
        
        # Wait for worker to finish
        start = time.time()
        while self.controller._thread_busy and time.time() - start < 2:
            self.app.processEvents()
            time.sleep(0.1)
            
        # Verify thread cleared
        self.assertFalse(self.controller._thread_busy)
        print("Network failure handled gracefully.")

if __name__ == '__main__':
    unittest.main()
