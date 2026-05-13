import pytest
from PySide6.QtCore import QRect, QRectF, QSizeF, QPoint
from PySide6.QtGui import QImage, QColor, QPainter, QTransform

from qpageview.constants import Rotate_0, Rotate_90
from qpageview.page import AbstractPage, BlankPage, ImagePrintPageMixin


class _MockPage(AbstractPage):
    def paint(self, painter, rect, callback=None):
        if callback:
            callback(self)

    def print(self, painter, rect=None, paperColor=None):
        if rect is None:
            rect = self.pageRect()
        painter.fillRect(rect, paperColor or QColor('green'))

    def image(self, rect=None, dpiX=None, dpiY=None, paperColor=None):
        if rect is None:
            rect = self.rect()
        if dpiX is None:
            dpiX = self.dpi
        if dpiY is None:
            dpiY = dpiX

        img = QImage(max(1, rect.width()), max(1, rect.height()), QImage.Format.Format_ARGB32)
        img.fill(paperColor or QColor('green'))
        return img

    def mutex(self):
        return None

class _MockImagePrintPage(ImagePrintPageMixin, _MockPage):
    def __init__(self):
        self._image_calls = []

    def image(self, rect=None, dpiX=None, dpiY=None, paperColor=None):
        self._image_calls.append((rect, dpiX, dpiY, paperColor))
        img = QImage(10, 10, QImage.Format.Format_ARGB32)
        img.fill(QColor("red"))
        return img


@pytest.fixture(scope="function")
def page():
    p = _MockPage()
    p.pageWidth = 200
    p.pageHeight = 100
    p.scaleX = 1.0
    p.scaleY = 1.0
    p.rotation = Rotate_0
    p.computedRotation = Rotate_0
    p.updateSize(72, 72, 1.0)
    return p

def test_abstract_page_set_page_size(page):
    page.setPageSize(QSizeF(321.5, 654.5))

    assert page.pageWidth == pytest.approx(321.5)
    assert page.pageHeight == pytest.approx(654.5)
    assert page.pageSize() == QSizeF(321.5, 654.5)

def test_abstract_page_page_rect(page):
    page.pageWidth = 123
    page.pageHeight = 456

    assert page.pageRect() == QRectF(0, 0, 123, 456)

def test_abstract_page_default_size(page):
    page.pageWidth = 200
    page.pageHeight = 100
    page.scaleX = 2.0
    page.scaleY = 3.0
    page.computedRotation = Rotate_0
    assert page.defaultSize() == QSizeF(400, 300)

    page.computedRotation = Rotate_90
    assert page.defaultSize() == QSizeF(300, 400)

def test_abstract_page_update_size(page):
    page.pageWidth = 100
    page.pageHeight = 50
    page.scaleX = 1.0
    page.scaleY = 1.0
    page.computedRotation = Rotate_0

    page.updateSize(144, 72, 2.0)

    assert page.width == 400
    assert page.height == 100

def test_abstract_page_zoom_width_and_height(page):
    page.pageWidth = 200
    page.pageHeight = 100
    page.scaleX = 2.0
    page.scaleY = 1.0
    page.computedRotation = Rotate_0
    page.dpi = 72.0

    z_w = page.zoomForWidth(100, Rotate_0, 72)
    z_h = page.zoomForHeight(100, Rotate_0, 72)

    assert z_w == pytest.approx(1.0)
    assert z_h == pytest.approx(1.0)

def test_abstract_page_copy_no_owner(page):
    page.x = 10
    page.y = 20
    page.width = 30
    page.height = 40

    copied = page.copy()

    assert copied is not page
    assert copied.geometry() == page.geometry()

def test_abstract_page_with_owner(page):
    class _MockObject:
        pass

    owner = _MockObject()

    c1 = page.copy(owner)
    c2 = page.copy(owner)

    assert c1 is c2

def test_abstract_page_copy_with_matrix(page):
    page.setGeometry(QRect(10, 20, 30, 40))
    m = QTransform()
    m.translate(5, 7)

    copied = page.copy(matrix=m)

    assert copied.geometry() == QRect(15, 27, 30, 40)

def test_abstract_page_map_to_from_page(page):
    page.setGeometry(QRect(0, 0, 200, 100))
    original = QPoint(50, 25)

    mapped = page.mapToPage().point(original)
    restored = page.mapFromPage().point(mapped)

    assert restored == original

def test_abstract_page_valid_device(page):
    img = QImage(200, 100, QImage.Format.Format_ARGB32)
    img.fill(QColor("green"))

    result = page.output(img, QRectF(0, 0, 50, 50), QColor("red"))

    assert result is True

def test_blank_page_dpi_and_color():
    page = BlankPage()
    page.pageWidth = 100
    page.pageHeight = 50
    page.scaleX = 1.0
    page.scaleY = 1.0
    page.computedRotation = Rotate_0

    image = page.image(dpiX=144, dpiY=72, paperColor=QColor("green"))

    assert image.width() == 200
    assert image.height() == 50
    assert image.pixelColor(0, 0) == QColor("green")

def test_blank_page_print():
    page = BlankPage()
    target = QImage(20, 20, QImage.Format.Format_ARGB32)
    target.fill(QColor("green"))
    painter = QPainter(target)

    page.print(painter, QRectF(5, 5, 10, 10), QColor("red"))
    painter.end()

    assert target.pixelColor(7, 7) == QColor("red")
    assert target.pixelColor(1, 1) == QColor("green")

def test_image_print_page_mixin_calls_image():
    page = _MockImagePrintPage()
    page.pageWidth = 100
    page.pageHeight = 100
    page.scaleX = 1.0
    page.scaleY = 1.0
    page.computedRotation = Rotate_0
    page.updateSize(72, 72, 1.0)

    target = QImage(40, 40, QImage.Format.Format_ARGB32)
    target.fill(QColor("green"))
    painter = QPainter(target)
    page.print(painter, QRectF(0, 0, 20 ,20), QColor("red"))
    painter.end()

    assert len(page._image_calls) == 1

def test_abstract_page_group_ident_and_group(page):
    assert page.group() is page
    assert page.ident() is None
