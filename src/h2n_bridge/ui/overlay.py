"""
H2N Bridge — Floating Overlay UI (Minimal Indicator)
=====================================================
A tiny pill-shaped indicator ~140×28 logical px.
Uses setWindowOpacity for fade (NOT QGraphicsOpacityEffect which
balloons the compositing layer to full-screen size on macOS).
"""

from __future__ import annotations

import math
from enum import Enum, auto

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtSignal,
    QObject,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QApplication, QWidget


# ─────────────────────────  Colour Palette  ──────────────────────────
class Palette:
    BG           = QColor(18, 18, 24, 215)
    BG_BORDER    = QColor(60, 60, 80, 140)
    ACCENT       = QColor(100, 140, 255)
    TEXT_PRIMARY = QColor(235, 235, 245)
    SUCCESS      = QColor(80, 220, 140)


class OverlayState(Enum):
    HIDDEN     = auto()
    LISTENING  = auto()
    PROCESSING = auto()
    COMPLETED  = auto()


# ────────────────────────  Signal Handler  ───────────────────────────
class SignalHandler(QObject):
    update_text   = pyqtSignal(str)
    show_window   = pyqtSignal()
    hide_window   = pyqtSignal()
    set_state     = pyqtSignal(str)
    set_amplitude = pyqtSignal(float)


# ────────────────────────  Main Overlay  ─────────────────────────────
class Overlay(QWidget):
    """
    Pure-paint pill widget.  No child widgets, no layouts, no
    QGraphicsEffect — nothing that can force Qt to resize the window.
    Fade is done via setWindowOpacity / QPropertyAnimation on the
    'windowOpacity' property which is natively supported.
    """

    W = 140
    H = 28

    def __init__(self, signal_handler: SignalHandler):
        super().__init__(None)
        self.signal_handler = signal_handler
        self._state      = OverlayState.HIDDEN
        self._phase      = 0.0
        self._amplitude  = 0.0
        self._check_prog = 0.0
        self._shimmer_x  = -0.3
        self._label      = ""
        self._anim: QPropertyAnimation | None = None

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)
        self._tick_timer.timeout.connect(self._tick)

        self._setup_window()
        self._connect_signals()

    # ── window flags ────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.ToolTip
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # setFixedSize BEFORE show — prevents Qt from computing a size hint
        self.setFixedSize(self.W, self.H)

        try:
            import AppKit
            ns_win = AppKit.NSApp.windowWithWindowNumber_(int(self.winId()))
            if ns_win:
                ns_win.setCanBecomeKeyWindow_(False)
                ns_win.setCanBecomeMainWindow_(False)
                ns_win.setLevel_(25)
        except Exception:
            pass

        self._reposition()
        self.hide()

    def _reposition(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        ag = screen.availableGeometry()
        self.move(ag.x() + (ag.width()  - self.W) // 2,
                  ag.y() + (ag.height() - self.H) // 2 - 140)

    # ── signals ─────────────────────────────────────────────────────
    def _connect_signals(self):
        self.signal_handler.update_text.connect(self._set_label)
        self.signal_handler.show_window.connect(self._on_show)
        self.signal_handler.hide_window.connect(self._fade_out)
        self.signal_handler.set_state.connect(self._on_set_state)
        self.signal_handler.set_amplitude.connect(
            lambda v: setattr(self, '_amplitude', max(0.0, min(1.0, v)))
        )

    def _set_label(self, text: str):
        self._label = text
        self.update()

    def _on_show(self):
        self.setWindowOpacity(1.0)
        self.show()

    def _on_set_state(self, name: str):
        self._transition_to({
            "listening":  OverlayState.LISTENING,
            "processing": OverlayState.PROCESSING,
            "completed":  OverlayState.COMPLETED,
        }.get(name, OverlayState.HIDDEN))

    # ── state machine ───────────────────────────────────────────────
    def _transition_to(self, state: OverlayState):
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._state      = state
        self._phase      = 0.0
        self._check_prog = 0.0
        self._shimmer_x  = -0.3

        if state == OverlayState.LISTENING:
            self._label = "דבר עכשיו"
            self.setWindowOpacity(1.0)
            self.show()
            self._tick_timer.start()

        elif state == OverlayState.PROCESSING:
            self._label = "מעבד…"
            self._tick_timer.start()

        elif state == OverlayState.COMPLETED:
            self._label = "סיום"
            self._tick_timer.start()
            QTimer.singleShot(1800, self._fade_out)

        elif state == OverlayState.HIDDEN:
            self._tick_timer.stop()
            self.hide()

        self.update()

    # ── animation tick ──────────────────────────────────────────────
    def _tick(self):
        self._phase += 0.07
        if self._state == OverlayState.PROCESSING:
            self._shimmer_x += 0.014
            if self._shimmer_x > 1.3:
                self._shimmer_x = -0.3
        elif self._state == OverlayState.COMPLETED:
            if self._check_prog < 1.0:
                self._check_prog = min(1.0, self._check_prog + 0.04)
        self.update()

    # ── painting ────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r    = h / 2.0
        rect = QRectF(0.5, 0.5, w - 1, h - 1)

        # Background pill
        pill = QPainterPath()
        pill.addRoundedRect(rect, r, r)

        if self._state == OverlayState.LISTENING:
            border = QColor(Palette.ACCENT);  border.setAlpha(170)
        elif self._state == OverlayState.COMPLETED:
            border = QColor(Palette.SUCCESS); border.setAlpha(170)
        else:
            border = Palette.BG_BORDER

        p.setPen(QPen(border, 1.0))
        p.setBrush(Palette.BG)
        p.drawPath(pill)

        # Shimmer (PROCESSING only)
        if self._state == OverlayState.PROCESSING:
            p.setClipPath(pill)
            sw = w * 0.35
            sx = self._shimmer_x * w
            sg = QLinearGradient(sx, 0, sx + sw, 0)
            sg.setColorAt(0.0, QColor(0, 0, 0, 0))
            sg.setColorAt(0.5, QColor(120, 160, 255, 50))
            sg.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(sg)
            p.drawRect(QRectF(sx, 0, sw, h))
            p.setClipping(False)

        cy = h / 2.0
        dx = 11.0   # dot centre-x
        dr = 3.5    # dot radius

        p.setPen(Qt.PenStyle.NoPen)

        if self._state == OverlayState.LISTENING:
            pulse = 0.5 + 0.5 * math.sin(self._phase * 1.8)
            glow  = QColor(Palette.ACCENT); glow.setAlpha(int(35 * pulse))
            p.setBrush(glow)
            p.drawEllipse(QPointF(dx, cy), dr + 3, dr + 3)
            dot = QColor(Palette.ACCENT); dot.setAlphaF(0.55 + 0.45 * pulse)
            p.setBrush(dot)
            p.drawEllipse(QPointF(dx, cy), dr, dr)

        elif self._state == OverlayState.PROCESSING:
            sp = 7.0
            bx = dx - sp
            for j in range(3):
                ph = self._phase + j * 0.9
                dy = -2.5 * abs(math.sin(ph))
                a  = 0.45 + 0.55 * abs(math.sin(ph))
                dc = QColor(Palette.ACCENT); dc.setAlphaF(a)
                p.setBrush(dc)
                p.drawEllipse(QPointF(bx + j * sp, cy + dy), 2.2, 2.2)

        elif self._state == OverlayState.COMPLETED:
            cr  = dr + 0.5
            bg2 = QColor(Palette.SUCCESS); bg2.setAlpha(28)
            p.setBrush(bg2)
            p.drawEllipse(QPointF(dx, cy), cr + 2, cr + 2)
            pen_c = QPen(Palette.SUCCESS, 1.5, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen_c); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(dx, cy), cr, cr)
            prog = self._check_prog
            if prog > 0:
                pt1 = QPointF(dx - cr * 0.42, cy)
                pt2 = QPointF(dx - cr * 0.05, cy + cr * 0.38)
                s1  = min(1.0, prog * 2)
                e1  = QPointF(pt1.x() + (pt2.x() - pt1.x()) * s1,
                              pt1.y() + (pt2.y() - pt1.y()) * s1)
                p.drawLine(pt1, e1)
                if prog > 0.4:
                    pt3 = QPointF(dx + cr * 0.48, cy - cr * 0.38)
                    s2  = min(1.0, (prog - 0.4) / 0.6)
                    e2  = QPointF(pt2.x() + (pt3.x() - pt2.x()) * s2,
                                  pt2.y() + (pt3.y() - pt2.y()) * s2)
                    p.drawLine(pt2, e2)

        # Label — pixel size so DPI scaling doesn't inflate it
        p.setPen(Palette.TEXT_PRIMARY)
        font = QFont("Helvetica Neue")
        font.setPixelSize(11)           # pixel size, not point size — DPI-safe
        font.setWeight(QFont.Weight.Medium)
        p.setFont(font)
        p.drawText(QRectF(20, 0, w - 26, h), Qt.AlignmentFlag.AlignCenter, self._label)

        p.end()

    # ── fade via windowOpacity ───────────────────────────────────────
    def _fade_out(self):
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(450)
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_fade_done)
        self._anim.start()

    def _on_fade_done(self):
        self._tick_timer.stop()
        self.hide()
        self.setWindowOpacity(1.0)
        self._state = OverlayState.HIDDEN


# ───────────────────────  Standalone Demo  ───────────────────────────
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    handler = SignalHandler()
    overlay = Overlay(handler)

    QTimer.singleShot(300,  lambda: handler.set_state.emit("listening"))
    QTimer.singleShot(4000, lambda: handler.set_state.emit("processing"))
    QTimer.singleShot(7000, lambda: handler.set_state.emit("completed"))

    sys.exit(app.exec())