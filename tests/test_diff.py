from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QPainter, QPixmap

from qpageview.diff import DiffPage, DiffDocument, DiffRenderer
from qpageview.page import BlankPage


class _MockPage:
    def __init__(self, dpi=72.0, width=100, height=200):
        self.dpi = dpi
        self.pageWidth = width
        self.pageHeight = height

def _filled_pixmap(w, h, color):
    pm = QPixmap(w, h)
    pm.fill(color)
    return pm

### createPages Tests ###
def test_diffpage_copies_dimensions():
    a1 = _MockPage(dpi=96.0, width=150, height=250)
    b1 = _MockPage(dpi=120.0, width=200, height=300)

    pages = list(DiffPage.createPages([[a1], [b1]]))  # type: ignore

    assert len(pages) == 1
    p = pages[0]
    assert p.dpi == 96.0
    assert p.pageWidth == 150
    assert p.pageHeight == 250
    assert p.pages == [a1, b1]

def test_diffpage_pads_shorter_lists():
    a1 = _MockPage(dpi=96.0, width=150, height=250)
    a2 = _MockPage(dpi=96.0, width=150, height=250)
    b1 = _MockPage(dpi=120.0, width=200, height=300)

    pages = list(DiffPage.createPages([[a1, a2], [b1]]))  # type: ignore

    assert len(pages) == 2

    assert pages[0].pages[0] is a1
    assert pages[0].pages[1] is b1
    assert pages[1].pages[0] is a2
    assert isinstance(pages[1].pages[1], BlankPage)

def test_diffpage_padded_page_has_same_dimensions():
    a1 = _MockPage(dpi=120.0, width=500, height=700)

    pages = list(DiffPage.createPages([[a1], []]))  # type: ignore
    assert len(pages) == 1

    blank = pages[0].pages[1]
    assert isinstance(blank, BlankPage)
    assert blank.dpi == 120.0
    assert blank.pageWidth == 500
    assert blank.pageHeight == 700

def test_diffpage_no_padding():
    a1 = _MockPage()
    a2 = _MockPage()
    b1 = _MockPage()

    pages = list(DiffPage.createPages([[a1, a2], [b1]], pad=None))  # type: ignore

    assert len(pages) == 1
    assert pages[0].pages == [a1, b1]


### DiffDocument Tests ###
def test_diffdocument_page_class():
    assert DiffDocument.pageClass is DiffPage

### DiffRenderer Tests ###
def test_diffrenderer_colors():
    r = DiffRenderer()
    assert len(r.colors) == 4
    assert r.colors[0] == QColor(Qt.GlobalColor.black)
    assert r.colors[1] == QColor(Qt.GlobalColor.red)
    assert r.colors[2] == QColor(Qt.GlobalColor.green)
    assert r.colors[3] == QColor(Qt.GlobalColor.blue)

def test_diffrenderer_combine(qapp):
    r = DiffRenderer()

    dest = _filled_pixmap(10, 10, QColor(Qt.GlobalColor.white))
    src = _filled_pixmap(4, 4, QColor(Qt.GlobalColor.black))

    painter = QPainter(dest)
    r.combine(painter, [(QPoint(2, 2), src)])
    painter.end()

    image = dest.toImage()
    assert image.pixelColor(0, 0) == QColor(Qt.GlobalColor.white)
    assert image.pixelColor(2, 2) == QColor(Qt.GlobalColor.black)

def test_diffrenderer_combine_skips_transparent(qapp):
    r = DiffRenderer()
    r.colors = [QColor(0, 0, 0, 0)]  # fully transparent

    dest = _filled_pixmap(10, 10, QColor(Qt.GlobalColor.white))
    src = _filled_pixmap(4, 4, QColor(Qt.GlobalColor.black))

    painter = QPainter(dest)
    r.combine(painter, [(QPoint(2, 2), src)])
    painter.end()

    image = dest.toImage()
    assert image.pixelColor(0, 0) == QColor(Qt.GlobalColor.white)
    assert image.pixelColor(2, 2) == QColor(Qt.GlobalColor.white)

def test_diffrenderer_combine_multiple(qapp):
    r = DiffRenderer()

    dest = _filled_pixmap(10, 10, QColor(Qt.GlobalColor.white))
    src1 = _filled_pixmap(4, 4, QColor(Qt.GlobalColor.black))
    src2 = _filled_pixmap(4, 4, QColor(Qt.GlobalColor.black))

    painter = QPainter(dest)
    r.combine(painter, [(QPoint(2, 2), src1), (QPoint(3, 3), src2)])
    painter.end()

    image = dest.toImage()
    assert image.pixelColor(2, 2) == QColor(Qt.GlobalColor.black)
    assert image.pixelColor(3, 3) == QColor(Qt.GlobalColor.black)
