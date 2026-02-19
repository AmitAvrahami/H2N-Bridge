import sys
import os
from dotenv import load_dotenv

def check_imports():
    print("Checking dependencies...")
    try:
        import sounddevice
        print("✅ sounddevice")
    except ImportError:
        print("❌ sounddevice missing")

    try:
        import numpy
        print("✅ numpy")
    except ImportError:
        print("❌ numpy missing")

    try:
        import faster_whisper
        print("✅ faster_whisper")
    except ImportError:
        print("❌ faster_whisper missing")

    try:
        import groq
        print("✅ groq")
    except ImportError:
        print("❌ groq missing")

    try:
        import PyQt6
        print("✅ PyQt6")
    except ImportError:
        print("❌ PyQt6 missing")
    
    try:
        import pynput
        print("✅ pynput")
    except ImportError:
        print("❌ pynput missing")

    try:
        import pyperclip
        print("✅ pyperclip")
    except ImportError:
        print("❌ pyperclip missing")

def check_env():
    print("\nChecking environment...")
    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    if key and key.startswith("gsk_"):
        print("✅ GROQ_API_KEY found")
    else:
        print("❌ GROQ_API_KEY missing or invalid in .env")
        print("   Please create .env file with GROQ_API_KEY=gsk_...")

if __name__ == "__main__":
    check_imports()
    check_env()
    print("\nIf all checks passed, you can run the app with:")
    print("python -m h2n_bridge.main")
