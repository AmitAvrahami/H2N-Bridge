from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QKeyEvent
from h2n_bridge.components.shortcut_manager import ShortcutManager

class SettingsWindow(QWidget):
    """
    UI for managing keyboard shortcuts.
    Allows recording new key combinations and saving them.
    """
    closed = pyqtSignal()
    
    def __init__(self, manager: ShortcutManager):
        super().__init__()
        self.manager = manager
        self.recording_action = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("H2N Bridge - Settings")
        self.setFixedWidth(400)
        
        # Frameless but with a title bar feeling
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                background-color: #333;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton#recordButton {
                background-color: #2c3e50;
            }
            QPushButton#recordButton:checked {
                background-color: #e74c3c;
                border-color: #c0392b;
            }
        """)

        layout = QVBoxLayout()
        
        header = QLabel("Keyboard Shortcuts")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("margin-bottom: 20px; color: #3498db;")
        layout.addWidget(header)

        # Container for shortcut rows
        self.rows_layout = QVBoxLayout()
        self.create_shortcut_row("translation_trigger", "Start/Stop Translation")
        self.create_shortcut_row("app_launch", "Open Settings")
        self.create_shortcut_row("app_exit", "Quit Application")
        
        layout.addLayout(self.rows_layout)
        layout.addStretch()
        
        info = QLabel("Click 'Record' then press your desired key combination.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; font-size: 11px; margin-top: 20px;")
        layout.addWidget(info)
        
        self.setLayout(layout)

    def create_shortcut_row(self, action_id, label_text):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 5, 0, 5)
        
        label = QLabel(label_text)
        current_key = self.manager.get_shortcut(action_id)
        key_label = QLabel(current_key)
        key_label.setStyleSheet("color: #f1c40f; font-weight: bold;")
        key_label.setObjectName(f"keyLabel_{action_id}")
        
        btn = QPushButton("Record")
        btn.setCheckable(True)
        btn.setObjectName(f"btn_{action_id}")
        btn.clicked.connect(lambda checked: self.toggle_record(action_id, checked))
        
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(key_label)
        row_layout.addWidget(btn)
        
        self.rows_layout.addWidget(row_widget)

    def toggle_record(self, action_id, checked):
        # If we were already recording something else, stop it
        if self.recording_action and self.recording_action != action_id:
            old_btn = self.findChild(QPushButton, f"btn_{self.recording_action}")
            if old_btn:
                old_btn.setChecked(False)
        
        if checked:
            self.recording_action = action_id
            self.grabKeyboard()
            key_label = self.findChild(QLabel, f"keyLabel_{action_id}")
            if key_label:
                key_label.setText("[Press Keys...]")
        else:
            self.recording_action = None
            self.releaseKeyboard()
            # Restore label
            key_label = self.findChild(QLabel, f"keyLabel_{action_id}")
            if key_label:
                key_label.setText(self.manager.get_shortcut(action_id))

    def keyPressEvent(self, event: QKeyEvent):
        if not self.recording_action:
            super().keyPressEvent(event)
            return

        # Ignore standalone modifier keys
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        # Build pynput compatible string
        parts = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("<ctrl>")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("<shift>")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("<alt>")
        if mods & Qt.KeyboardModifier.MetaModifier:
            parts.append("<cmd>")
            
        key_text = self.qt_key_to_pynput(event.key())
        if key_text:
            parts.append(key_text)
            
        combo = "+".join(parts)
        
        # Try to update
        if self.manager.update_shortcut(self.recording_action, combo):
            # Success
            btn = self.findChild(QPushButton, f"btn_{self.recording_action}")
            if btn:
                btn.setChecked(False)
            self.toggle_record(self.recording_action, False)
        else:
            # Conflict / Error
            key_label = self.findChild(QLabel, f"keyLabel_{self.recording_action}")
            if key_label:
                key_label.setText("CONFLICT!")
                key_label.setStyleSheet("color: #e74c3c;")
                QTimer.singleShot(1000, lambda: self.reset_label(self.recording_action))

    def reset_label(self, action_id):
        key_label = self.findChild(QLabel, f"keyLabel_{action_id}")
        if key_label:
            key_label.setText(self.manager.get_shortcut(action_id))
            key_label.setStyleSheet("color: #f1c40f; font-weight: bold;")

    def qt_key_to_pynput(self, qt_key):
        # Map common keys
        mapping = {
            Qt.Key.Key_K: "k",
            Qt.Key.Key_Q: "q",
            Qt.Key.Key_L: "l",
            Qt.Key.Key_T: "t",
            Qt.Key.Key_S: "s",
            Qt.Key.Key_A: "a",
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Return: "enter",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
        }
        
        if qt_key in mapping:
            return mapping[qt_key]
        
        # Fallback for simple alphanumeric
        text = QKeyEvent(QKeyEvent.Type.KeyPress, qt_key, Qt.KeyboardModifier.NoModifier).text().lower()
        if text and text.isalnum():
            return text
            
        return None

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
