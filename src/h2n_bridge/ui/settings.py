import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QKeyEvent, QColor
from h2n_bridge.components.shortcut_manager import ShortcutManager

class SettingsWindow(QWidget):
    """
    Visually appealing UI for managing keyboard shortcuts, 
    matching the aesthetic of the main recording overlay.
    """
    closed = pyqtSignal()
    
    def __init__(self, manager: ShortcutManager):
        super().__init__()
        self.manager = manager
        self.recording_action = None
        self._drag_pos = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("H2N Bridge - Settings")
        self.setFixedSize(450, 260)
        
        # Make the window frameless and translucent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Inner frame for the rounded corners and background
        self.bg_frame = QFrame(self)
        self.bg_frame.setObjectName("bgFrame")
        self.bg_frame.setStyleSheet("""
            QFrame#bgFrame {
                background-color: rgba(18, 18, 24, 230);
                border: 1px solid rgba(60, 60, 80, 140);
                border-radius: 16px;
            }
            QLabel {
                color: rgb(235, 235, 245);
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            }
            QPushButton {
                background-color: rgba(60, 60, 80, 140);
                color: rgb(235, 235, 245);
                border: 1px solid rgba(100, 140, 255, 100);
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: rgba(100, 140, 255, 80);
            }
            QPushButton:checked {
                background-color: rgba(220, 80, 80, 180);
                border: 1px solid rgba(255, 100, 100, 200);
                color: white;
            }
            QPushButton#closeBtn {
                background-color: transparent;
                border: none;
                color: rgba(235, 235, 245, 150);
                font-size: 16px;
                padding: 0px;
                min-width: 20px;
            }
            QPushButton#closeBtn:hover {
                color: white;
            }
        """)

        # Layout inside the frame
        frame_layout = QVBoxLayout(self.bg_frame)
        frame_layout.setContentsMargins(24, 20, 24, 24)

        # Header Header
        header_layout = QHBoxLayout()
        header = QLabel("Settings & Shortcuts")
        font = QFont("Helvetica Neue", 16, QFont.Weight.Bold)
        header.setFont(font)
        header.setStyleSheet("color: rgb(100, 140, 255);")
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.hide)

        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        frame_layout.addLayout(header_layout)
        
        # Subtitle
        subtitle = QLabel("Click 'Record' and press a key combination to update.")
        subtitle.setStyleSheet("color: rgba(235, 235, 245, 120); font-size: 12px; margin-bottom: 12px;")
        frame_layout.addWidget(subtitle)

        # Container for shortcut rows
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(12)
        
        self.create_shortcut_row("translation_trigger", "Start/Stop Translation")
        self.create_shortcut_row("app_launch", "Open Settings (This Window)")
        self.create_shortcut_row("app_exit", "Quit Application")
        
        frame_layout.addLayout(self.rows_layout)
        frame_layout.addStretch()

        main_layout.addWidget(self.bg_frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def create_shortcut_row(self, action_id, label_text):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(label_text)
        label.setFont(QFont("Helvetica Neue", 13))
        
        current_key = self.manager.get_shortcut(action_id)
        key_label = QLabel(current_key)
        key_label.setStyleSheet("color: rgb(80, 220, 140); font-family: monospace; font-size: 13px; font-weight: bold; background-color: rgba(255,255,255,10); padding: 4px 8px; border-radius: 4px;")
        key_label.setObjectName(f"keyLabel_{action_id}")
        
        btn = QPushButton("Record")
        btn.setCheckable(True)
        btn.setObjectName(f"btn_{action_id}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda checked: self.toggle_record(action_id, checked))
        
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(key_label)
        # Spacer
        row_layout.addSpacing(16)
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
                key_label.setStyleSheet("color: rgb(255, 180, 80); font-family: monospace; font-size: 13px; font-weight: bold; background-color: rgba(255,180,80,20); padding: 4px 8px; border-radius: 4px;")
        else:
            self.recording_action = None
            self.releaseKeyboard()
            self.reset_label(action_id)

    def keyPressEvent(self, event: QKeyEvent):
        if not self.recording_action:
            super().keyPressEvent(event)
            return

        # Ignore standalone modifier keys to wait for the final combination
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        # Build pynput compatible string
        parts = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.MetaModifier:
            parts.append("<cmd>")
        if mods & Qt.KeyboardModifier.ControlModifier:
            parts.append("<ctrl>")
        if mods & Qt.KeyboardModifier.AltModifier:
            parts.append("<alt>")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            parts.append("<shift>")
            
        key_text = self.qt_key_to_pynput(event.key(), event.text())
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
                key_label.setStyleSheet("color: rgb(250, 80, 80); font-family: monospace; font-size: 13px; font-weight: bold; background-color: rgba(250,80,80,20); padding: 4px 8px; border-radius: 4px;")
                QTimer.singleShot(1500, lambda: self.reset_label(self.recording_action))

    def reset_label(self, action_id):
        key_label = self.findChild(QLabel, f"keyLabel_{action_id}")
        if key_label:
            key_label.setText(self.manager.get_shortcut(action_id))
            key_label.setStyleSheet("color: rgb(80, 220, 140); font-family: monospace; font-size: 13px; font-weight: bold; background-color: rgba(255,255,255,10); padding: 4px 8px; border-radius: 4px;")

    def qt_key_to_pynput(self, qt_key, text):
        # Map common keys that pynput treats specially
        mapping = {
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
            Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3",
            Qt.Key.Key_F4: "f4", Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6",
            Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8", Qt.Key.Key_F9: "f9",
            Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
        }
        
        if qt_key in mapping:
            return mapping[qt_key]
            
        # For standard letters A-Z, Qt.Key enum values match ASCII uppercase
        if Qt.Key.Key_A <= qt_key <= Qt.Key.Key_Z:
            return chr(qt_key).lower()
            
        # Fallback for standard characters
        if text and text.isprintable():
            return text.lower()
            
        return None

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
