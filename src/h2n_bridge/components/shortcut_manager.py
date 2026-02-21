import json
import os
import threading
import platform
from typing import Dict, Callable, Optional
from PyQt6.QtCore import QObject

class ShortcutManager(QObject):
    """
    Manages keyboard shortcuts: loading from config, checking conflicts,
    and running the global listener thread.
    Inherits from QObject to handle signals if using the macOS native listener.
    """
    
    def __init__(self, config_path: str = "config.json"):
        super().__init__()
        self.config_path = config_path
        self.shortcuts: Dict[str, str] = {}
        self.callbacks: Dict[str, Callable] = {}
        self._listener = None 
        self._lock = threading.Lock()
        self._pending_restart = False
        
        self.load_config()

    def load_config(self):
        """Loads shortcuts from the JSON config file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                    self.shortcuts = data.get("shortcuts", {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading shortcut config: {e}")
                self.shortcuts = {}
        else:
            # Default shortcuts if file doesn't exist
            self.shortcuts = {
                "translation_trigger": "<ctrl>+k",
                "app_exit": "<ctrl>+q",
                "app_launch": "<ctrl>+l"
            }
            self.save_config()

    def save_config(self):
        """Saves current shortcuts to the JSON config file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump({"shortcuts": self.shortcuts}, f, indent=2)
        except IOError as e:
            print(f"Error saving shortcut config: {e}")

    def register_callback(self, action: str, callback: Callable):
        """Registers a function to be called when a specific action's shortcut is triggered."""
        self.callbacks[action] = callback

    def update_shortcut(self, action: str, new_key: str, restart_callback=None) -> bool:
        with self._lock:
            for existing_action, existing_key in self.shortcuts.items():
                if existing_key == new_key and existing_action != action:
                    print(f"Conflict: {new_key} is already assigned to {existing_action}")
                    return False
            
            self.shortcuts[action] = new_key
            self.save_config()
            
            self._pending_restart = True
            return True

    def _on_triggered(self, action: str):
        """Internal bridge to call the registered callback for an action."""
        if action in self.callbacks:
            self.callbacks[action]()

    def _on_mac_hotkey_triggered(self, callback_func):
        """Helper to invoke the action from the macOS native thread."""
        callback_func()

    def start_listener(self):
        """Starts the global hotkey listener in the current thread (should be spawned as daemon)."""
        self.stop_listener()
        
        # ── macOS CRASH FIX: Use Native AppKit Instead of Pynput ──
        if platform.system() == "Darwin":
            from src.h2n_bridge.components.mac_hotkeys import MacHotkeyListener, parse_hotkey
            
            hotkey_map = {}
            for action, key_combo in self.shortcuts.items():
                # Parse the pynput-style string into macOS native keycodes/modifiers
                keycode, modifiers = parse_hotkey(key_combo)
                if keycode is not None:
                    # Create a closure
                    def handler(a=action):
                        self._on_triggered(a)
                    hotkey_map[(keycode, modifiers)] = handler
                    
            self._listener = MacHotkeyListener(hotkey_map)
            self._listener.hotkey_triggered.connect(self._on_mac_hotkey_triggered)
            self._listener.start()
        else:
            # Fallback to pynput for non-macOS systems:
            from pynput import keyboard as pynput_keyboard
            
            hotkey_map = {}
            for action, key_combo in self.shortcuts.items():
                def handler(a=action):
                    self._on_triggered(a)
                hotkey_map[key_combo] = handler

            try:
                self._listener = pynput_keyboard.GlobalHotKeys(hotkey_map)
                self._listener.start()
            except Exception as e:
                print(f"Failed to start hotkey listener: {e}")

    def stop_listener(self):
        """Stops the existing listener if it's running."""
        if self._listener:
            self._listener.stop()
            self._listener = None

    def restart_listener(self):
        """Restarts the listener to apply new configuration."""
        self.start_listener()

    def get_shortcut(self, action: str) -> str:
        """Returns the current key combination for an action."""
        return self.shortcuts.get(action, "")
