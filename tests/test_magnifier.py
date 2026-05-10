import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent, QPaintEvent
from PySide6.QtWidgets import QWidget

from qpageview import magnifier
from qpageview.magnifier import Magnifier, DRAG_SHORT, DRAG_LONG

class _MockCopiedPage:
    def __init__(self, rect):
        self._rect = QRect(rect)
        self.paint_calls = []

    def geometry(self):
        return QRect(self._rect)

    def pos(self):
        return self._rect.topLeft()

    def paint(self, painter, rect, callback):
        self.paint_calls.append((painter, QRect(rect), callback))

class _MockPage:
    def __init__(self, rect):
        self._rect = QRect(rect)
        self.copy_calls = []
        self.copied_pages = []

    def copy(self, parent, matrix):
        self.copy_calls.append((parent, matrix))
        copied = _MockCopiedPage(self._rect)
        self.copied_pages.append(copied)
        return copied

class _MockLayout:
    def __init__(self, pages=None):
        self.zoomFactor = 1.0
        self.spacing = 8
        self._pages = list(pages) if pages else []
        self.pages_at_calls = []

    def pagesAt(self, rect):
        self.pages_at_calls.append(QRect(rect))
        return self._pages

class _MockView(QWidget):
    MIN_ZOOM = 0.1
    MAX_ZOOM = 4.0
    dropShadowEnabled = False

    def __init__(self, layout):
        super().__init__()
        self._layout = layout
        self._layout_pos = QPoint(0, 0)
        self.scroll_for_dragging_calls = []
        self.stop_scrolling_calls = 0
        self.draw_drop_shadow_calls = []

    def pageLayout(self):
        return self._layout

    def layoutPosition(self):
        return QPoint(self._layout_pos)

    def setLayoutPosition(self, pos):
        self._layout_pos = QPoint(pos)

    def scrollForDragging(self, delta):
        self.scroll_for_dragging_calls.append(QPoint(delta))

    def stopScrolling(self):
        self.stop_scrolling_calls += 1

    def drawDropShadow(self, page, painter, width):
        self.draw_drop_shadow_calls.append((page, painter, width))

@pytest.fixture(scope="function")
def magnifier_parent(qtbot):
    layout = _MockLayout()
    view = _MockView(layout)
    viewport = QWidget(view)
    viewport.resize(400, 300)
    qtbot.addWidget(view)
    qtbot.addWidget(viewport)

    magnifier = Magnifier()
    magnifier.setParent(viewport)
    magnifier.resize(120, 120)
    magnifier.hide()
    return magnifier, viewport, view, layout

def test_magnifier_initial_state(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent

    assert magnifier.isHidden()
    assert magnifier.scale() == 3.0
    assert magnifier.width() == 120
    assert magnifier.height() == 120

def test_magnifier_move(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent

    magnifier.resize(100, 80)
    magnifier.moveCenter(QPoint(200, 150))

    assert magnifier.geometry().center() == QPoint(200, 150)

def test_magnifier_update_scale(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent

    magnifier.setScale(2.5)

    assert magnifier.scale() == 2.5

def test_magnifier_start_short_drag(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    view.show()
    viewport.show()

    magnifier.startShortDrag(QPoint(50, 60))

    assert magnifier.isVisible() is True
    assert magnifier._dragging == DRAG_SHORT
    assert magnifier.geometry().center() == QPoint(50, 60)
    assert viewport.cursor().shape() == Qt.CursorShape.BlankCursor

def test_magnifier_end_short_drag(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    view.show()
    viewport.show()

    magnifier.startShortDrag(QPoint(50, 60))
    magnifier.endShortDrag()

    assert magnifier.isHidden() is True
    assert magnifier._dragging is False
    assert magnifier._resizepos is None
    assert viewport.cursor().shape() == Qt.CursorShape.ArrowCursor
    assert view.stop_scrolling_calls == 1

def test_magnifier_start_long_drag(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent

    magnifier.startLongDrag(QPoint(70, 80))

    assert magnifier._dragging == DRAG_LONG
    assert magnifier._dragpos == QPoint(70, 80)
    assert magnifier.cursor().shape() == Qt.CursorShape.ClosedHandCursor

def test_magnifier_end_long_drag(magnifier_parent):
    magnifier, _, view, _ = magnifier_parent

    magnifier.startLongDrag(QPoint(20, 25))
    magnifier.endLongDrag()

    assert magnifier._dragging is False
    assert view.stop_scrolling_calls == 1

def test_magnifier_event_filter_short_drag(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    view.show()
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(40, 45),
        QPointF(40, 45),
        QPointF(40, 45),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier
    )

    handled = magnifier.eventFilter(viewport, ev)

    assert handled is True
    assert magnifier.isVisible() is True
    assert magnifier._dragging == DRAG_SHORT
    assert magnifier.geometry().center() == QPoint(40, 45)

def test_magnifier_event_filter_ignore_press(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    view.show()
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(40, 45),
        QPointF(40, 45),
        QPointF(40, 45),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    handled = magnifier.eventFilter(viewport, ev)

    assert handled is False
    assert magnifier.isHidden() is True

def test_magnifier_event_filter_short_drag_and_scroll(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    magnifier.startShortDrag(QPoint(10, 10))
    view.show()
    ev = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(70, 80),
        QPointF(70, 80),
        QPointF(70, 80),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    handled = magnifier.eventFilter(viewport, ev)

    assert handled is True
    assert magnifier.geometry().center() == QPoint(70, 80)
    assert view.scroll_for_dragging_calls[-1] == QPoint(70, 80)

def test_magnifier_event_filter_both_buttons(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    magnifier.startShortDrag(QPoint(100, 100))
    view.show()

    original_center = magnifier.geometry().center()
    original_width = magnifier.width()

    first_move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(100, 100),
        QPointF(100, 100),
        QPointF(100, 100),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier
    )
    second_move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(100, 120),
        QPointF(100, 120),
        QPointF(100, 120),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier
    )

    assert magnifier.eventFilter(viewport, first_move) is True
    assert magnifier.eventFilter(viewport, second_move) is True

    assert magnifier.width() > original_width
    assert magnifier.height() == magnifier.width()
    assert magnifier.geometry().center() == original_center

def test_magnifier_event_filter_short_drag_release(magnifier_parent):
    magnifier, viewport, view, _ = magnifier_parent
    magnifier.startShortDrag(QPoint(20, 20))
    view.show()

    ev = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(20, 20),
        QPointF(20, 20),
        QPointF(20, 20),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )

    handled = magnifier.eventFilter(viewport, ev)

    assert handled is True
    assert magnifier.isHidden() is True
    assert magnifier._dragging is False

def test_magnifier_long_drag(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent
    magnifier.show()
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(30, 30),
        QPointF(30, 30),
        QPointF(30, 30),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    magnifier.mousePressEvent(ev)

    assert magnifier._dragging == DRAG_LONG
    assert magnifier._dragpos == QPoint(30, 30)

def test_magnifier_long_drag_move(magnifier_parent):
    magnifier, _, view, _ = magnifier_parent

    view.show()
    magnifier.show()

    magnifier.startLongDrag(QPoint(10, 10))
    ev = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(40, 50),
        QPointF(40, 50),
        QPointF(40, 50),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    magnifier.mouseMoveEvent(ev)

    assert magnifier.pos() == QPoint(30, 40)
    assert view.scroll_for_dragging_calls[-1] == QPoint(40, 50)

def test_magnifier_long_drag_release(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent
    magnifier.show()

    magnifier.startLongDrag(QPoint(5, 5))
    ev = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(5, 5),
        QPointF(5, 5),
        QPointF(5, 5),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )

    magnifier.mouseReleaseEvent(ev)

    assert magnifier._dragging is False

def test_magnifier_mouse_wheel_with_zoom(magnifier_parent):
    magnifier, _, _, layout = magnifier_parent
    layout.zoomFactor = 2.0
    magnifier.setScale(2.0)

    ev = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False
    )

    magnifier.wheelEvent(ev)

    assert magnifier.scale() == pytest.approx(2.2)

def test_magnifier_mouse_wheel_without_resize(magnifier_parent):
    magnifier, _, _, _ = magnifier_parent
    magnifier.setGeometry(50, 60, 120, 120)
    original_center = magnifier.geometry().center()
    ev = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )

    magnifier.wheelEvent(ev)

    assert magnifier.width() > 120
    assert magnifier.height() == magnifier.width()
    assert magnifier.geometry().center() == original_center

def test_magnifier_mouse_wheel_clamps(magnifier_parent):
    magnifier, _, view, layout = magnifier_parent
    layout.zoomFactor = 1.0
    magnifier.setScale(100.0)

    zoom_in = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(),
        QPoint(0, -1200),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    magnifier.wheelEvent(zoom_in)
    assert magnifier.scale() == pytest.approx(view.MAX_ZOOM * magnifier.MAX_EXTRA_ZOOM / layout.zoomFactor)

    magnifier.setScale(0.01)
    zoom_out = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    magnifier.wheelEvent(zoom_out)
    assert magnifier.scale() == pytest.approx(view.MIN_ZOOM / layout.zoomFactor)

def test_magnifier_paint_event(magnifier_parent):
    magnifier, _, _, layout = magnifier_parent
    page = _MockPage(QRect(0, 0, 200, 200))
    layout._pages = [page]
    magnifier.show()
    magnifier.setGeometry(50, 50, 100, 100)

    magnifier.paintEvent(QPaintEvent(magnifier.rect()))

    assert len(layout.pages_at_calls) == 1
    assert len(page.copy_calls) == 1
    assert len(page.copied_pages[0].paint_calls) == 1

def test_magnifier_repaint_update(magnifier_parent, monkeypatch):
    magnifier, _, _, _ = magnifier_parent
    updates = []
    monkeypatch.setattr(magnifier, "update", lambda: updates.append(True))

    magnifier.repaintPage(object())  # type: ignore

    assert updates == [True]
