import pytest
from PySide6.QtCore import QPoint, QRect, QSize, QEvent, Qt
from PySide6.QtGui import QColor, QContextMenuEvent, QImage, QMouseEvent
from PySide6.QtWidgets import QWidget

from qpageview.rubberband import Rubberband, _OUTSIDE, _LEFT, _TOP, _RIGHT, _BOTTOM, _INSIDE


class _MockPage:
    def __init__(self, geom):
        self._geom = QRect(geom)
        self._text = ""
        self._links = set()

    def geometry(self):
        return QRect(self._geom)

    def pos(self):
        return self._geom.topLeft()

    def text(self, _):
        return self._text

    def linksIn(self, _):
        return set(self._links)

    def image(self, rect, _, __, paperColor):
        img = QImage(max(1, rect.width()), max(1, rect.height()), QImage.Format.Format_ARGB32)
        img.fill(paperColor or QColor("green"))
        return img

class _MockLayout:
    def __init__(self, pages=None):
        self._pages = list(pages or [])
        self._offset = (-1, 0.0, 0.0)

    def pagesAt(self, rect):
        return [p for p in self._pages if p.geometry().intersects(rect)]

    def pos2offset(self, _):
        return self._offset

    def offset2pos(self, _):
        return QPoint(10, 20)

class _MockView(QWidget):
    def __init__(self, layout):
        super().__init__()
        self._layout = layout
        self._layout_pos = QPoint(0, 0)
        self._zoom = 1.0
        self._view_mode = 0
        self.scroll_calls = []
        self.stop_calls = 0

    def pageLayout(self):
        return self._layout

    def layoutPosition(self):
        return QPoint(self._layout_pos)

    def zoomFactor(self):
        return self._zoom

    def physicalDpiX(self):
        return 100

    def viewMode(self):
        return self._view_mode

    def scrollForDragging(self, pos):
        self.scroll_calls.append(QPoint(pos))

    def stopScrolling(self):
        self.stop_calls += 1


@pytest.fixture(scope="function")
def rb_tuple(qtbot):
    layout = _MockLayout()
    view = _MockView(layout)
    viewport = QWidget(view)
    viewport.resize(400, 300)
    qtbot.addWidget(view)
    qtbot.addWidget(viewport)

    rb = Rubberband()
    rb.setParent(viewport)
    rb.hide()
    return rb, viewport, view, layout

def test_rubberband_has_selection(rb_tuple):
    rb, _, _, _ = rb_tuple
    rb._selection = QRect()

    assert rb.hasSelection() is False

    rb._selection = QRect(1, 2, 3, 4)
    assert rb.hasSelection() is True
    assert rb.selection() == QRect(1, 2, 3, 4)

def test_rubberband_set_selection(rb_tuple):
    rb, _, view, _ = rb_tuple
    view.show()

    emitted = []
    rb.selectionChanged.connect(lambda rect: emitted.append(QRect(rect)))

    rb.setSelection(QRect(5, 6, 30, 40))

    assert rb.isVisible() is True
    assert rb.selection() == QRect(5, 6, 30, 40)
    assert emitted[-1] == QRect(5, 6, 30, 40)

def test_rubberband_clear_selection(rb_tuple):
    rb, _, view, _ = rb_tuple
    view.show()

    rb.setSelection(QRect(5, 6, 30, 40))
    rb.clearSelection()

    assert rb.isVisible() is False
    assert rb.selection() == QRect()
    assert rb._dragging is False

def test_rubberband_selected_pages(rb_tuple):
    rb, _, _, layout = rb_tuple
    p1 = _MockPage(QRect(0, 0, 50, 50))
    p2 = _MockPage(QRect(40, 40, 50, 50))
    layout._pages = [p1, p2]
    rb._selection = QRect(30, 30, 30, 30)

    selected = list(rb.selectedPages())

    assert len(selected) == 2
    assert selected[0][1].isValid()
    assert selected[1][1].isValid()

def test_rubberband_selected_page_largest_intersection(rb_tuple):
    rb, _, _, layout = rb_tuple
    p1 = _MockPage(QRect(0, 0, 100, 100))
    p2 = _MockPage(QRect(90, 90, 20, 20))
    layout._pages = [p1, p2]
    rb._selection = QRect(10, 10, 60, 60)

    page, rect = rb.selectedPage()

    assert page is p1
    assert rect is not None
    assert rect.width() > 0
    assert rect.height() > 0

def test_rubberband_selected_image_default_resolution(rb_tuple):
    rb, _, view, layout = rb_tuple
    p = _MockPage(QRect(0, 0, 100, 100))
    layout._pages = [p]
    rb._selection = QRect(10, 10, 20, 20)

    image = rb.selectedImage(paperColor=QColor("green"))

    assert isinstance(image, QImage)
    assert image.width() > 0
    assert image.height() > 0
    assert image.pixelColor(0, 0) == QColor("green")

def test_rubberband_selected_text(rb_tuple):
    rb, _, _, layout = rb_tuple
    p1 = _MockPage(QRect(0, 0, 50, 50))
    p2 = _MockPage(QRect(40, 40, 50, 50))
    p1._text = "Page 1 text"
    p2._text = "Page 2 text"
    layout._pages = [p1, p2]
    rb._selection = QRect(30, 30, 30, 30)

    text = rb.selectedText()

    assert text == "Page 1 text\nPage 2 text"

def test_rubberband_selected_links(rb_tuple):
    rb, _, _, layout = rb_tuple
    p1 = _MockPage(QRect(0, 0, 50, 50))
    p2 = _MockPage(QRect(40, 40, 50, 50))
    p1._links = {"a"}
    p2._links = set()
    layout._pages = [p1, p2]
    rb._selection = QRect(30, 30, 30, 30)

    links = list(rb.selectedLinks())

    assert len(links) == 1
    assert links[0][0] is p1
    assert links[0][1] == {"a"}

def test_rubberband_drag_by(rb_tuple):
    rb, _, _, _ = rb_tuple
    rb._draggeom = QRect(100, 100, 20, 20)
    rb._dragedge = _LEFT | _TOP
    rb.trackSelection = True
    emitted = []
    rb.selectionChanged.connect(lambda rect: emitted.append(QRect(rect)))

    rb.dragBy(QPoint(10, 10))

    assert rb.geometry().isValid()
    assert len(emitted) >= 1

def test_rubberband_stop_drag_clears_small_selection(rb_tuple):
    rb, _, view, _ = rb_tuple
    rb._dragging = True
    rb.setGeometry(QRect(10, 10, 4, 4))

    rb.stopDrag()

    assert rb._dragging is False
    assert rb.selection() == QRect()
    assert view.stop_calls == 1

def test_rubberband_stop_drag_keeps_large_selection(rb_tuple):
    rb, _, view, _ = rb_tuple
    rb._dragging = True
    rb.setGeometry(QRect(10, 10, 20, 20))

    rb.stopDrag()

    assert rb._dragging is False
    assert rb.selection().isValid()
    assert view.stop_calls == 1

def test_rubberband_zoom_changed(rb_tuple):
    rb, _, _, _ = rb_tuple
    rb._selection = QRect(1, 1, 10, 10)
    rb._oldZoom = 1.0
    rb.setGeometry(QRect(10, 20, 40, 40))

    rb.slotZoomChanged(2.0)

    assert rb.geometry().width() == 80
    assert rb.geometry().height() == 80

def test_rubberband_mouse_press_starts_drag(rb_tuple):
    rb, _, _, _ = rb_tuple
    rb.setGeometry(QRect(10, 10, 100, 80))
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPoint(20, 20),
        QPoint(20, 20),
        QPoint(20, 20),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    rb.mousePressEvent(ev)

    assert rb._dragging is True
    assert rb._dragbutton == Qt.MouseButton.LeftButton

def test_rubberband_mouse_move_updates_drag(monkeypatch, rb_tuple):
    rb, _, _, _ = rb_tuple
    rb._dragging = True
    called = []
    monkeypatch.setattr(rb, "drag", lambda pos: called.append(QPoint(pos)))
    ev = QMouseEvent(
        QEvent.Type.MouseMove,
        QPoint(30, 30),
        QPoint(30, 30),
        QPoint(30, 30),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )

    rb.mouseMoveEvent(ev)

    assert called[-1] == QPoint(30, 30)

def test_rubberband_mouse_release_stops_drag(monkeypatch, rb_tuple):
    rb, _, _, _ = rb_tuple
    rb._dragging = True
    rb._dragbutton = Qt.MouseButton.LeftButton
    called = []
    monkeypatch.setattr(rb, "stopDrag", lambda: called.append(True))
    ev = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPoint(30, 30),
        QPoint(30, 30),
        QPoint(30, 30),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )

    rb.mouseReleaseEvent(ev)

    assert called == [True]
