import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QMouseEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from qpageview.util import LongMousePressMixin


class MockLongMousePressMixin(LongMousePressMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.received = []
        self.longMousePressTime = 40
        self.longMousePressTolerance = 3

    def longMousePressEvent(self, ev: QMouseEvent) -> None:
        pos = ev.position().toPoint()
        self.received.append((QPoint(pos.x(), pos.y()), ev.button(), ev.modifiers()))


@pytest.fixture(scope="function")
def widget(qtbot):
    w = MockLongMousePressMixin()
    w.resize(200, 200)
    w.show()
    qtbot.addWidget(w)
    return w


def test_triggers_after_hold(widget, qtbot, offset_point):
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, offset_point)
    qtbot.wait(widget.longMousePressTime + 30)

    assert len(widget.received) == 1
    pos, button, modifiers = widget.received[0]
    assert pos == offset_point
    assert button == Qt.MouseButton.LeftButton
    assert modifiers == Qt.KeyboardModifier.NoModifier

def test_no_trigger_if_released_early(widget, qtbot, offset_point):
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, offset_point)
    qtbot.waitUntil(lambda: widget._longPressTimer is not None, timeout=500)

    QTest.mouseRelease(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, offset_point)
    qtbot.waitUntil(lambda: widget._longPressTimer is None, timeout=1000)
    qtbot.wait(widget.longMousePressTime + 100)

    assert len(widget.received) == 0

def test_move_beyond_tolerance_cancels(widget, qtbot, offset_point):
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, offset_point)
    qtbot.wait(max(1, widget.longMousePressTime // 2))
    QTest.mouseMove(widget, offset_point + QPoint(widget.longMousePressTolerance + 1, 0))
    qtbot.wait(widget.longMousePressTime + 20)

    assert len(widget.received) == 0

def test_move_within_tolerance_still_triggers(widget, qtbot, offset_point):
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, offset_point)
    QTest.mouseMove(widget, offset_point + QPoint(2, 1))
    qtbot.wait(widget.longMousePressTime + 20)

    assert len(widget.received) == 1

def test_disabled_skips_long_press(widget, qtbot, offset_point):
    widget.longMousePressEnabled = False
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, offset_point)
    qtbot.wait(widget.longMousePressTime + 30)

    assert len(widget.received) == 0
