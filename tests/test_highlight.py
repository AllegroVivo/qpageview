import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap

import qpageview
from qpageview.highlight import Highlighter


@pytest.fixture(scope="function")
def view(qtbot):
    v = qpageview.View()
    v.resize(40, 300)
    v.show()
    qtbot.addWidget(v)
    return v


### Highlighter Tests ###
def test_highlighter_defaults():
    highlighter = Highlighter()
    assert highlighter.lineWidth == 2
    assert highlighter.radius == 3
    assert highlighter.color is None

def test_highlighter_custom_color(qapp):
    h = Highlighter()
    h.color = QColor("green")

    pm = QPixmap(100, 100)
    pm.fill(QColor("white"))
    painter = QPainter(pm)
    h.paintRects(painter, [QRectF(10, 10, 30, 30)])
    painter.end()

    img = pm.toImage()
    # Some pixel near the drawn rect should be red (border is drawn around the rect)
    changed = any(
        QColor(img.pixel(x, y)) == QColor("green")
        for x in range(5, 45)
        for y in range(5, 45)
    )
    assert changed

def test_highlighter_no_rects(qapp):
    h = Highlighter()
    h.color = QColor("green")

    pm = QPixmap(100, 100)
    pm.fill(QColor("white"))
    painter = QPainter(pm)
    h.paintRects(painter, [])
    painter.end()

    img = pm.toImage()
    for x in range(50):
        for y in range(50):
            assert QColor(img.pixel(x, y)) == QColor("white")

def test_highlighter_custom_width_and_radius(qapp):
    h = Highlighter()
    h.color = QColor("green")
    h.lineWidth = 5
    h.radius = 0

    pm = QPixmap(100, 100)
    pm.fill(QColor("white"))
    painter = QPainter(pm)
    h.paintRects(painter, [QRectF(30, 30, 20, 20)])
    painter.end()

    img = pm.toImage()
    changed = any(
        QColor(img.pixel(x, y)) == QColor("green")
        for x in range(100)
        for y in range(100)
    )
    assert changed

### HighlightViewMixin Tests ###
def test_default_highlighter_creation(view):
    h = view.defaultHighlighter()
    assert isinstance(h, Highlighter)

def test_default_highlighter_singleton(view):
    h1 = view.defaultHighlighter()
    h2 = view.defaultHighlighter()
    assert h1 is h2

def test_set_default_highlighter(view):
    h = Highlighter()
    view.setDefaultHighlighter(h)
    assert view.defaultHighlighter() is h

def test_highlighting_state(view):
    # Should be off by default
    assert view.isHighlighting() is False
    # Turn on by calling highlight() with an empty area
    view.highlight({})
    assert view.isHighlighting() is True
    # Clear the highlighting
    view.clearHighlight()
    assert view.isHighlighting() is False
    view.clearHighlight()  # should not cause error when already cleared

def test_explicit_highlighter(view):
    h = Highlighter()
    view.highlight({}, highlighter=h)
    assert view.isHighlighting(h) is True
    assert view.isHighlighting() is False

def test_highlighter_replacement(view):
    h1 = Highlighter()
    h2 = Highlighter()
    view.highlight({}, highlighter=h1)
    view.highlight({}, highlighter=h2)

    view.clearHighlight(h1)

    assert view.isHighlighting(h1) is False
    assert view.isHighlighting(h2) is True

def test_highlight_timeout(view, qtbot):
    view.highlight({}, msec=80)
    assert view.isHighlighting() is True

    qtbot.waitUntil(lambda: not view.isHighlighting(), timeout=1000)
    assert view.isHighlighting() is False

def test_highlight_manual_clear_timeout(view, qtbot):
    view.highlight({}, msec=500)
    view.clearHighlight()

    qtbot.wait(600)
    assert view.isHighlighting() is False
