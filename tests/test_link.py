import pytest
from PySide6.QtCore import QPoint, QEvent, Qt, QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QWidget

from qpageview.cupsprinter import PAGE_SIZES
from qpageview.link import Link, Links, LinkViewMixin


class _MockPage:
    def __init__(self, links=None, x=0, y=0):
        self._links = links or []
        self._pos = QPoint(x, y)

    def pos(self):
        return QPoint(self._pos)

    def linksAt(self, _point):
        return self._links

class _MockLayout:
    def __init__(self, page=None):
        self._page = page

    def pageAt(self, _pos):
        return self._page

class _MockHighlighter:
    pass

class _MockLinkWidget(LinkViewMixin, QWidget):
    def __init__(self):
        super().__init__()
        self._pageLayout = _MockLayout()
        self._layout_pos = QPoint(0, 0)
        self.highlight_calls = []
        self.clear_highlight_calls = []
        self.adjust_cursor_super_called = False
        self.mouse_press_super_called = False
        self.event_super_called = False
        self.leave_super_called = False

    def layoutPosition(self):
        return QPoint(self._layout_pos)

    def setLayoutPosition(self, p):
        self._layout_pos = QPoint(p)

    def highlight(self, areas, highlighter, msec):
        self.highlight_calls.append((areas, highlighter, msec))

    def clearHighlight(self, highlighter):
        self.clear_highlight_calls.append(highlighter)

    def adjustCursor(self, pos) -> None:
        if getattr(self, "_inside_link_mixin", False):
            self.adjust_cursor_super_called = True
            return
        self._inside_link_mixin = True
        try:
            LinkViewMixin.adjustCursor(self, pos)
        finally:
            self._inside_link_mixin = False

    def mousePressEvent(self, ev):
        if getattr(self, "_inside_mouse_mixin", False):
            self.mouse_press_super_called = True
            return
        self._inside_mouse_mixin = True
        try:
            super().mousePressEvent(ev)
        finally:
            self._inside_mouse_mixin = False

    def event(self, ev) -> bool:
        if getattr(self, "_inside_event_mixin", False):
            self.event_super_called = True
            return False
        self._inside_event_mixin = True
        try:
            return super().event(ev)
        finally:
            self._inside_event_mixin = False

    def leaveEvent(self, ev):
        if getattr(self, "_inside_leave_mixin", False):
            self.leave_super_called = True
            return
        self._inside_leave_mixin = True
        try:
            super().leaveEvent(ev)
        finally:
            self._inside_leave_mixin = False


@pytest.fixture(scope="function")
def link():
    return Link(0.1, 0.2, 0.3, 0.4, url="https://example.com", tooltip="tip")

@pytest.fixture(scope="function")
def widget(qtbot):
    w = _MockLinkWidget()
    w.resize(200, 100)
    qtbot.addWidget(w)
    return w


def test_link_initializes_correctly():
    l1 = Link(0, 0, 1, 1, url="https://example.com", tooltip="Example")
    l2 = Link(0, 0, 1, 1, url="relative/path")
    l3 = Link(0, 0, 1, 1)

    assert l1.url == "https://example.com"
    assert l1.tooltip == "Example"
    assert l1.isExternal is True
    assert l2.isExternal is False
    assert l3.url == ""

def link_rect_returns_expected():
    l = Link(0.1, 0.2, 0.8, 0.9)

    r = l.rect()

    assert r.left() == pytest.approx(0.1)
    assert r.top() == pytest.approx(0.2)
    assert r.right() == pytest.approx(0.8)
    assert r.bottom() == pytest.approx(0.9)

def test_links_intersecting():
    l1 = Link(0.0, 0.0, 0.2, 0.2)
    l2 = Link(0.6, 0.6, 0.9, 0.9)
    links = Links([l1, l2])

    hits = list(links.intersecting(0.0, 0.0, 0.3, 0.3))

    assert l1 in hits
    assert l2 not in hits

def test_link_highlighter_set_and_remove(widget):
    h = _MockHighlighter()

    widget.setLinkHighlighter(h)  # type: ignore
    assert widget.linkHighlighter() is h

    widget.setLinkHighlighter(None)
    assert widget.linkHighlighter() is None

def test_link_at_with_page(widget, link):
    page = _MockPage(links=[link])
    widget._pageLayout = _MockLayout(page=page)

    p, l = widget.linkAt(QPoint(10, 10))

    assert p is page
    assert l is link

def test_link_at_no_page(widget):
    widget._pageLayout = _MockLayout(page=None)
    assert widget.linkAt(QPoint(10, 10)) == (None, None)

    widget._pageLayout = _MockLayout(page=_MockPage(links=[]))
    assert widget.linkAt(QPoint(10, 10)) == (None, None)

def test_adjust_cursor_link_an_signals(widget, link):
    page = _MockPage(links=[link])
    widget._pageLayout = _MockLayout(page=page)

    hovered = []
    left = []
    widget.linkHovered.connect(lambda p, l: hovered.append((p, l)))
    widget.linkLeft.connect(lambda: left.append(True))

    widget.linkHoverEnter(page, link)  # type: ignore
    assert hovered == [(page, link)]
    assert widget.cursor().shape() == Qt.CursorShape.PointingHandCursor

    widget.linkHoverLeave()
    assert left == [True]

def test_link_hover_highlighting(widget, link):
    page = _MockPage(links=[link])
    h = _MockHighlighter()
    widget.setLinkHighlighter(h)  # type: ignore

    widget.linkHoverEnter(page, link)  # type: ignore
    assert len(widget.highlight_calls) == 1
    areas, highlighter, timeout = widget.highlight_calls[0]
    assert page in areas
    assert highlighter is h
    assert timeout == 3000

    widget.linkHoverLeave()
    assert widget.clear_highlight_calls == [h]

def test_link_mouse_press(widget, link):
    page = _MockPage(links=[link])
    widget._pageLayout = _MockLayout(page=page)

    clicked = []
    widget.linkClicked.connect(lambda ev, p, l: clicked.append((ev, p, l)))

    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        QPointF(10, 10),
        QPointF(10, 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    widget.mousePressEvent(ev)

    assert len(clicked) == 1
    assert clicked[0][1] is page
    assert clicked[0][2] is link
    assert widget.mouse_press_super_called is False

def test_mouse_press_no_link(widget, link):
    page = _MockPage(links=[link])
    widget._pageLayout = _MockLayout(page=page)

    called = []
    widget.linkHelpRequested.connect(lambda ev, p, l: called.append((ev, p, l)))

    ev = QMouseEvent(
        QEvent.Type.ToolTip,
        QPointF(4, 4),
        QPointF(4, 4),
        QPointF(4, 4),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )

    result = widget.event(ev)

    assert result is True
    assert len(called) == 1
    assert called[0][1] is page
    assert called[0][2] is link

def test_mouse_help_event_no_link(widget, link):
    widget._pageLayout = _MockLayout(page=_MockPage(links=[]))

    called = []
    widget.linkHelpRequested.connect(lambda ev, p, l: called.append((ev, p, l)))

    ev1 = QMouseEvent(
        QEvent.Type.ToolTip,
        QPointF(2, 2),
        QPointF(2, 2),
        QPointF(2, 2),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    widget.event(ev1)
    assert called == []

    widget.linksEnabled = False
    widget._pageLayout = _MockLayout(page=_MockPage(links=[link]))

    called = []
    widget.linkHelpRequested.connect(lambda ev, p, l: called.append((ev, p, l)))

    ev2 = QMouseEvent(
        QEvent.Type.WhatsThis,
        QPointF(2, 2),
        QPointF(2, 2),
        QPointF(2, 2),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    widget.event(ev2)
    assert called == []

def test_leave_event(widget, link):
    page = _MockPage(links=[link])
    widget._pageLayout = _MockLayout(page=page)
    widget.adjustCursor(QPoint(5, 5))
    assert widget._currentLinkId is not None

    left = []
    widget.linkLeft.connect(lambda: left.append(True))

    ev = QMouseEvent(
        QEvent.Type.Leave,
        QPointF(0, 0),
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    widget.leaveEvent(ev)

    assert widget._currentLinkId is None
    assert len(left) == 1
