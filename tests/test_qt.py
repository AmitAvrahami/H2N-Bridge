import sys
try:
    from PyQt6.QtWidgets import QApplication
    print("Imported QApplication successfully")
    app = QApplication(sys.argv)
    print("Created QApplication successfully")
except Exception as e:
    print(f"Error: {e}")
