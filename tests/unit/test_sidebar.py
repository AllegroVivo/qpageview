import pytest
from PySide6.QtCore import QEvent, QSize, QPoint, Qt, QMargins
from PySide6.QtGui import QWheelEvent, QKeyEvent, QResizeEvent

from qpageview.constants import Vertical, Horizontal, FitWidth, FitHeight
from qpageview.sidebarview import SidebarView

@pytest.fixture(scope="function")
def sidebar(qtbot):
    v = SidebarView()
    v.resize(240, 480)
    qtbot.addWidget(v)
    return v


def test_sidebar_initial_values(sidebar):
    assert sidebar.orientation() == Vertical
    assert sidebar.viewMode() == FitWidth
    assert sidebar.pageLayout().spacing == 1
    assert sidebar.pageLayout().margins() == QMargins(0, 0, 0, 0)
    assert sidebar.pageLayout().pageMargins() == QMargins(4, 4, 4, 16)

def test_sidebar_set_orientation(sidebar):
    sidebar.setOrientation(Vertical)
    assert sidebar.viewMode() == FitWidth

    sidebar.setOrientation(Horizontal)
    assert sidebar.viewMode() == FitHeight

def test_sidebar_set_layout_font_height(sidebar):
    old_bottom = sidebar.pageLayout().pageMargins().bottom()

    sidebar.setLayoutFontHeight()

    assert sidebar.pageLayout().pageMargins().bottom() >= old_bottom

def test_sidebar_wheel_event_positive_delta(monkeypatch, sidebar):
    called = {"prev": 0, "next": 0}
    monkeypatch.setattr(sidebar, "gotoPreviousPage", lambda: called.update({"prev": called["prev"] + 1}))
    monkeypatch.setattr(sidebar, "gotoNextPage", lambda: called.update({"next": called["next"] + 1}))

    ev = QWheelEvent(
        QPoint(10, 10),
        QPoint(10, 10),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    sidebar.wheelEvent(ev)

    assert called["prev"] == 1
    assert called["next"] == 0

def test_sidebar_wheel_event_negative_delta(monkeypatch, sidebar):
    called = {"prev": 0, "next": 0}
    monkeypatch.setattr(sidebar, "gotoPreviousPage", lambda: called.update({"prev": called["prev"] + 1}))
    monkeypatch.setattr(sidebar, "gotoNextPage", lambda: called.update({"next": called["next"] + 1}))

    ev = QWheelEvent(
        QPoint(10, 10),
        QPoint(10, 10),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    sidebar.wheelEvent(ev)

    assert called["prev"] == 0
    assert called["next"] == 1

def test_sidebar_key_press_down_and_page_down(monkeypatch, sidebar):
    called = {"next": 0}
    monkeypatch.setattr(sidebar, "gotoNextPage", lambda: called.update({"next": called["next"] + 1}))

    ev_down = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Down,
        Qt.KeyboardModifier.NoModifier
    )
    ev_pgdn = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_PageDown,
        Qt.KeyboardModifier.NoModifier
    )

    sidebar.keyPressEvent(ev_down)
    sidebar.keyPressEvent(ev_pgdn)

    assert called["next"] == 2

def test_sidebar_key_press_up_and_page_up(monkeypatch, sidebar):
    called = {"prev": 0}
    monkeypatch.setattr(sidebar, "gotoPreviousPage", lambda: called.update({"prev": called["prev"] + 1}))

    ev_up = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Up,
        Qt.KeyboardModifier.NoModifier
    )
    ev_pgup = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_PageUp,
        Qt.KeyboardModifier.NoModifier
    )

    sidebar.keyPressEvent(ev_up)
    sidebar.keyPressEvent(ev_pgup)

    assert called["prev"] == 2

def test_sidebar_key_press_home_and_end(monkeypatch, sidebar):
    called = {"num": []}
    monkeypatch.setattr(sidebar, "pageCount", lambda: 9)
    monkeypatch.setattr(sidebar, "setCurrentPageNumber", lambda n: called["num"].append(n))

    ev_end = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_End,
        Qt.KeyboardModifier.NoModifier
    )
    ev_home = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Home,
        Qt.KeyboardModifier.NoModifier
    )

    sidebar.keyPressEvent(ev_end)
    sidebar.keyPressEvent(ev_home)

    assert called["num"] == [9, 1]

def test_sidebar_resize_event_auto_switch_to_horizontal(sidebar):
    sidebar.autoOrientationEnabled = True
    sidebar.setOrientation(Vertical)

    ev = QResizeEvent(QSize(500, 200), QSize(240, 480))
    sidebar.resizeEvent(ev)

    assert sidebar.orientation() == Horizontal
    assert sidebar.viewMode() == FitHeight

def test_sidebar_resize_event_auto_switch_to_vertical(sidebar):
    sidebar.autoOrientationEnabled = True
    sidebar.setOrientation(Horizontal)

    ev = QResizeEvent(QSize(200, 500), QSize(480, 240))
    sidebar.resizeEvent(ev)

    assert sidebar.orientation() == Vertical
    assert sidebar.viewMode() == FitWidth

def test_sidebar_resize_event_auto_disabled(sidebar):
    sidebar.autoOrientationEnabled = False
    sidebar.setOrientation(Vertical)

    ev = QResizeEvent(QSize(500, 200), QSize(240, 480))
    sidebar.resizeEvent(ev)

    assert sidebar.orientation() == Vertical
    assert sidebar.viewMode() == FitWidth

def test_sidebar_font_change_event(monkeypatch, sidebar):
    called = {"count": 0}
    monkeypatch.setattr(sidebar, "setLayoutFontHeight", lambda: called.update({"count": called["count"] + 1}))

    ev = QEvent(QEvent.Type.FontChange)
    sidebar.changeEvent(ev)

    assert called["count"] == 1

def test_sidebar_application_font_change_event(monkeypatch, sidebar):
    called = {"count": 0}
    monkeypatch.setattr(sidebar, "setLayoutFontHeight", lambda: called.update({"count": called["count"] + 1}))

    ev = QEvent(QEvent.Type.ApplicationFontChange)
    sidebar.changeEvent(ev)

    assert called["count"] == 1

def test_sidebar_slot_current_page_number_changed(monkeypatch, sidebar):
    called = {"update": 0}
    monkeypatch.setattr(sidebar.viewport(), "update", lambda: called.update({"update": called["update"] + 1}))

    sidebar.slotCurrentPageNumberChanged(7)

    assert sidebar._currentPageNumber == 7
    assert called["update"] == 1
