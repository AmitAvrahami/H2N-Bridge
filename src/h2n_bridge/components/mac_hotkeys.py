import threading
from typing import Dict, Callable
from PyQt6.QtCore import QThread, pyqtSignal
import sys
import platform

# Only import AppKit on macOS
if platform.system() == "Darwin":
    try:
        import AppKit
    except ImportError:
        AppKit = None
else:
    AppKit = None

# A mapping from pynput-style key strings to macOS keycodes.
# This is a basic map and might need expansion for all possible keys.
MAC_KEYCODE_MAP = {
    'a': 0, 's': 1, 'd': 2, 'f': 3, 'h': 4, 'g': 5, 'z': 6, 'x': 7, 'c': 8, 'v': 9,
    'b': 11, 'q': 12, 'w': 13, 'e': 14, 'r': 15, 'y': 16, 't': 17, '1': 18, '2': 19,
    '3': 20, '4': 21, '6': 22, '5': 23, '=': 24, '9': 25, '7': 26, '-': 27, '8': 28,
    '0': 29, ']': 30, 'o': 31, 'u': 32, '[': 33, 'i': 34, 'p': 35, 'l': 37, 'j': 38,
    "'": 39, 'k': 40, ';': 41, '\\': 42, ',': 43, '/': 44, 'n': 45, 'm': 46, '.': 47,
    '`': 50,
    '<space>': 49,
    '<enter>': 36,
    '<esc>': 53,
    '<backspace>': 51,
}

# Mapping pynput modifier strings to AppKit modifier flags
if AppKit:
    MAC_MODIFIER_MAP = {
        '<shift>': AppKit.NSEventModifierFlagShift,
        '<ctrl>': AppKit.NSEventModifierFlagControl,
        '<alt>': AppKit.NSEventModifierFlagOption,
        '<cmd>': AppKit.NSEventModifierFlagCommand,
    }
else:
    MAC_MODIFIER_MAP = {}

def parse_hotkey(hotkey_str: str):
    """
    Parses a string like '<ctrl>+k' or '<cmd>+<shift>+p' into a (keycode, modifiers) tuple.
    Modifiers are bitwise OR'd AppKit flags.
    """
    if not AppKit:
        return None, 0

    parts = hotkey_str.lower().split('+')
    modifiers = 0
    keycode = None

    for part in parts:
        if part in MAC_MODIFIER_MAP:
            modifiers |= MAC_MODIFIER_MAP[part]
        elif part in MAC_KEYCODE_MAP:
            keycode = MAC_KEYCODE_MAP[part]
        else:
             # Try to map a single character directly if we missed it in the dictionary
             if len(part) == 1 and part.isalpha():
                 # We probably need a more exhaustive map for a production app,
                 # but for basic shortcuts this approach mostly works.
                 print(f"Warning: Unknown key '{part}' in shortcut '{hotkey_str}'. Map may be incomplete.")
                 pass

    return keycode, modifiers

class MacHotkeyListener(QThread):
    """
    A PyQt6 QThread that runs an AppKit global event monitor.
    Emits a signal when a matching hotkey is pressed.
    """
    hotkey_triggered = pyqtSignal(object) # Emits the callback closure

    def __init__(self, hotkey_map: Dict[tuple, Callable]):
        super().__init__()
        self.hotkey_map = hotkey_map
        self.monitor = None
        self._is_running = True

    def run(self):
        if not AppKit:
            print("AppKit not available, cannot start MacHotkeyListener.")
            return

        pool = AppKit.NSAutoreleasePool.alloc().init()
        mask = AppKit.NSEventMaskKeyDown
        
        def handler(event):
            if not self._is_running:
                return
            
            keycode = event.keyCode()
            raw_flags = event.modifierFlags()
            # We filter out device-independent flags to just get Shift, Ctrl, Option, Cmd
            flags = raw_flags & (AppKit.NSEventModifierFlagShift | 
                                 AppKit.NSEventModifierFlagControl | 
                                 AppKit.NSEventModifierFlagOption | 
                                 AppKit.NSEventModifierFlagCommand)
            
            for (map_keycode, map_modifiers), callback in self.hotkey_map.items():
                if keycode == map_keycode and flags == map_modifiers:
                    self.hotkey_triggered.emit(callback)
                    return 
            
        self.monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, handler)
        print("macOS native global hotkey listener started via AppKit.")
        
        # Run a tight run loop checking if we've been stopped
        run_loop = AppKit.NSRunLoop.currentRunLoop()
        while self._is_running:
            run_loop.runMode_beforeDate_(AppKit.NSDefaultRunLoopMode, AppKit.NSDate.dateWithTimeIntervalSinceNow_(0.1))
            
        if self.monitor:
            AppKit.NSEvent.removeMonitor_(self.monitor)
        
        del pool
        print("macOS native global hotkey listener stopped.")

    def stop(self):
        """Signals the thread to stop and waits for it."""
        self._is_running = False
        self.wait()

