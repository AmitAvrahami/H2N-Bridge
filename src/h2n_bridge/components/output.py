import pyperclip
import time
import platform
from pynput.keyboard import Key, Controller

# Use pynput instead of 'keyboard' module — pynput works without root on macOS

class OutputHandler:
    def __init__(self):
        self.os_type = platform.system()
        self.keyboard = Controller()

    def copy_to_clipboard(self, text):
        """Copies text to clipboard."""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            print(f"Clipboard Error: {e}", flush=True)
            return False

    def type_text(self, text):
        """Types the text or pastes it (faster)."""
        if not text:
            return

        # Method 1: Copy and Paste (Fastest & Safest for large text)
        self.copy_to_clipboard(text)
        
        # Small delay to ensure clipboard is ready
        time.sleep(0.15)
        
        # Trigger Paste
        if self.os_type == "Darwin": # macOS
            import subprocess
            try:
                # Use AppleScript to send Cmd+V to the frontmost application.
                # This is often more reliable than low-level keyboard simulation for focus handling.
                subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "v" using {command down}'], check=True)
            except Exception as e:
                print(f"AppleScript Paste Error: {e}", flush=True)
                # Fallback to pynput
                with self.keyboard.pressed(Key.cmd):
                    self.keyboard.press('v')
                    self.keyboard.release('v')
        else: # Windows/Linux
            with self.keyboard.pressed(Key.ctrl):
                self.keyboard.press('v')
                self.keyboard.release('v')

    def insert(self, text):
        """Main method to insert translated text into the active window."""
        self.type_text(text)

if __name__ == "__main__":
    # Test
    # handler = OutputHandler()
    # handler.insert("Hello World")
    pass
