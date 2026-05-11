import math

import pytest
from PySide6.QtCore import QPoint, QSize, QRect, Qt
from PySide6.QtGui import QWheelEvent, QMouseEvent, QKeyEvent

from qpageview.scrollarea import ScrollArea, SteadyScroller, KineticScroller
from qpageview.util import Point


@pytest.fixture(scope="function")
def scrollarea(qtbot):
    w = ScrollArea()
    w.resize(200, 150)
    w.show()
    qtbot.addWidget(w)
    return w

def test_scrollarea_set_area_size(scrollarea):
    scrollarea.setAreaSize(QSize(100, 80))

    assert scrollarea.areaSize() == QSize(100, 80)
    pos = scrollarea.areaPos()
    assert pos.x() >= 0
    assert pos.y() >= 0

def test_scrollarea_area_pos_scrollbar_offset(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    scrollarea.horizontalScrollBar().setValue(20)
    scrollarea.verticalScrollBar().setValue(30)

    pos = scrollarea.areaPos()

    assert pos == Point(-20, -30)

def test_scrollarea_visible_area(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    scrollarea.horizontalScrollBar().setValue(15)
    scrollarea.verticalScrollBar().setValue(25)

    visible = scrollarea.visibleArea()

    assert visible.x() == 15
    assert visible.y() == 25
    assert visible.width() <= scrollarea.viewport().width()
    assert visible.height() <= scrollarea.viewport().height()

def test_scrollarea_offset_to_ensure_visible_already_visible(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    scrollarea.scrollTo(Point(50, 50))
    rect = QRect(60, 60, 20, 20)

    diff = scrollarea.offsetToEnsureVisible(rect)

    assert diff == Point(0, 0)

def test_scrollarea_offset_to_ensure_visible_hidden_rect(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    scrollarea.scrollTo(Point(0, 0))
    rect = QRect(300, 200, 20, 20)

    diff = scrollarea.offsetToEnsureVisible(rect)

    assert diff.x() > 0
    assert diff.y() > 0

def test_scrollarea_offset_to_ensure_visible_direct_scroll(monkeypatch, scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    called = {"scroll_by": None}
    monkeypatch.setattr(scrollarea, "scrollBy", lambda d: called.__setitem__("scroll_by", d) or Point(d.x(), d.y()))
    rect = QRect(300, 250, 20, 20)

    scrollarea.ensureVisible(rect, allowKinetic=False)

    assert isinstance(called["scroll_by"], Point)

def test_scrollarea_offset_to_ensure_visible_kinetic_scroll(monkeypatch, scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    called = {"kinetic": None}
    monkeypatch.setattr(scrollarea, "kineticScrollBy", lambda d: called.__setitem__("kinetic", d) or Point(d.x(), d.y()))
    rect = QRect(300, 250, 20, 20)

    scrollarea.ensureVisible(rect, allowKinetic=True)

    assert isinstance(called["kinetic"], Point)

def test_scrollarea_can_scroll_by_clamps_scrollbar(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    scrollarea.scrollTo(Point(0, 0))

    diff = scrollarea.canScrollBy(Point(-100, -100))
    assert diff == Point(0, 0)

    diff2 = scrollarea.canScrollBy(Point(10_000, 10_000))
    assert diff2.x() == scrollarea.horizontalScrollBar().maximum()
    assert diff2.y() == scrollarea.verticalScrollBar().maximum()

def test_scrollarea_scroll_to_and_scroll_by(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    moved = scrollarea.scrollTo(Point(40, 30))

    assert moved == Point(40, 30)
    assert scrollarea.scrollOffset() == Point(40, 30)

    moved2 = scrollarea.scrollBy(Point(10, -5))
    assert moved2 == Point(10, -5)
    assert scrollarea.scrollOffset() == Point(50, 25)

def test_scrollarea_kinetic_scroll_by(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    moved = scrollarea.kineticScrollBy(Point(100, 50))

    assert moved == Point(100, 50)
    assert scrollarea.isScrolling() is True

def test_scrollarea_kinetic_add_delta(scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    scrollarea.kineticScrollBy(Point(100, 0))
    assert isinstance(scrollarea._scroller, KineticScroller)
    before = scrollarea._scroller.remainingDistance()

    scrollarea.kineticAddDelta(Point(50, 0))
    after = scrollarea._scroller.remainingDistance()

    assert abs(after.x()) > abs(before.x())

def test_scrollarea_steady_scroll_and_stop_scrolling(scrollarea):
    scrollarea.steadyScroll(Point(100, 0))
    assert scrollarea.isScrolling() is True
    assert isinstance(scrollarea._scroller, SteadyScroller)

    scrollarea.stopScrolling()
    assert scrollarea.isScrolling() is False

def test_scrollarea_remaining_scroll_time_non_kinetic_scroller(scrollarea):
    scrollarea.steadyScroll(Point(100, 0))

    assert scrollarea.remainingScrollTime() == 0

def test_scrollarea_kinetic_scroller(scrollarea):
    scrollarea.kineticScrollBy(Point(200, 0))

    assert scrollarea.remainingScrollTime() > 0

def test_scrollarea_is_dragging(scrollarea):
    assert scrollarea.isDragging() is False
    scrollarea._dragPos = QPoint(1, 1)
    assert scrollarea.isDragging() is True

def test_scrollarea_scroll_for_dragging(monkeypatch, scrollarea):
    called = {"diff": None}
    monkeypatch.setattr(scrollarea, "steadyScroll", lambda d: called.__setitem__("diff", d))

    scrollarea.scrollForDragging(QPoint(-10, -10))

    assert isinstance(called["diff"], Point)

def test_scrollarea_wheel_event_kinetic_add_delta(monkeypatch, scrollarea):
    called = {"delta": None}
    monkeypatch.setattr(scrollarea, "kineticAddDelta", lambda d: called.__setitem__("delta", d))

    ev = QWheelEvent(
        scrollarea.viewport().rect().center(),
        scrollarea.viewport().mapToGlobal(scrollarea.viewport().rect().center()),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False
    )
    scrollarea.wheelEvent(ev)

    assert called["delta"] == Point(0, -120)

def test_scrollarea_key_press_page_keys_kinetic_delta(monkeypatch, scrollarea):
    called = []
    monkeypatch.setattr(scrollarea, "kineticAddDelta", lambda d: called.append(d))
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)

    scrollarea.keyPressEvent(ev)

    assert len(called) == 1
    assert called[0].y() == scrollarea.verticalScrollBar().pageStep()

def test_scrollarea_mouse_drag_scrolls(monkeypatch, scrollarea):
    scrollarea.setAreaSize(QSize(500, 400))
    started = {"diff": None}
    monkeypatch.setattr(scrollarea, "kineticScrollBy", lambda d: started.__setitem__("diff", d) or Point(d.x(), d.y()))

    press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPoint(50, 50),
        QPoint(50, 50),
        QPoint(50, 50),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    move = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPoint(40, 40),
        QPoint(40, 40),
        QPoint(40, 40),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    release = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPoint(40, 40),
        QPoint(40, 40),
        QPoint(40, 40),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )

    scrollarea.mousePressEvent(press)
    scrollarea.mouseMoveEvent(move)
    scrollarea.mouseReleaseEvent(release)

    assert scrollarea._dragPos is None
    assert started["diff"] is None or isinstance(started["diff"], Point)

def test_steady_scroller():
    s = SteadyScroller(Point(-100, 50), 10)

    step = s.step()

    assert step.x() <= 0
    assert step.y() >= 0
    assert s.finished() is False

def test_kinetic_scroller():
    s = KineticScroller()
    s.scrollBy(Point(30, -20))
    rem_before = s.remainingDistance()
    ticks_before = s.remainingTicks()

    step = s.step()
    rem_after = s.remainingDistance()
    ticks_after = s.remainingTicks()

    assert isinstance(step, Point)
    assert abs(rem_after.x()) <= abs(rem_before.x())
    assert abs(rem_after.y()) <= abs(rem_before.y())
    assert ticks_after <= ticks_before

    while not s.finished():
        s.step()
    assert s.remainingTicks() == 0
