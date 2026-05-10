import pytest
from PySide6.QtCore import QPoint, QRect, QRectF
from PySide6.QtGui import QImage, QPainter, QColor

from qpageview.constants import Rotate_90, Rotate_180
from qpageview.multipage import MultiPage, MultiPageRenderer, CallBack


class _MockSubPage:
    def __init__(self, name="p", x=0, y=0, w=100, h=100):
        self.name = name
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.pageWidth = w
        self.pageHeight = h
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.rotation = 0
        self.computedRotation = 0
        self.dpi = 100.0
        self.renderer = None
        self._links = []
        self.update_size_calls = []
        self.paint_calls = []
        self.print_calls = []
        self.image_calls = []
        self.text_value = None

    def copy(self, _=None, __=None):
        cp = _MockSubPage(self.name, self.x, self.y, self.width, self.height)
        cp.pageWidth = self.pageWidth
        cp.pageHeight = self.pageHeight
        cp.scaleX = self.scaleX
        cp.scaleY = self.scaleY
        cp.rotation = self.rotation
        cp.computedRotation = self.computedRotation
        cp.dpi = self.dpi
        cp.renderer = self.renderer
        cp._links = list(self._links)
        cp.text_value = self.text_value
        return cp

    def updateSize(self, dpiX, dpiY, zoomFactor):
        self.update_size_calls.append((dpiX, dpiY, zoomFactor))
        self.width = int(round(self.pageWidth * zoomFactor))
        self.height = int(round(self.pageHeight * zoomFactor))

    def rect(self):
        return QRect(0, 0, self.width, self.height)

    def geometry(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def setGeometry(self, rect):
        self.x = rect.x()
        self.y = rect.y()
        self.width = rect.width()
        self.height = rect.height()

    def pos(self):
        return QPoint(self.x, self.y)

    def pageRect(self):
        return QRectF(0, 0, self.pageWidth, self.pageHeight)

    def paint(self, _, rect, callback=None):
        self.paint_calls.append((QRect(rect), callback))
        if callback:
            callback(self)

    def print(self, painter, rect=None):
        self.print_calls.append(QRectF(rect) if rect is not None else None)

    def image(self, rect, dpiX, dpiY, paperColor):
        self.image_calls.append((QRect(rect), dpiX, dpiY, paperColor))
        img = QImage(max(1, rect.width()), max(1, rect.height()), QImage.Format.Format_ARGB32)
        img.fill(QColor("green"))
        return img

    def text(self, _):
        return self.text_value

    def linksAt(self, point):
        return [l for l in self._links if self.linkRect(l).toRect().contains(point)]

    def linksIn(self, rect):
        return {l for l in self._links if self.linkRect(l).intersects(QRectF(rect))}

    def links(self):
        return list(self._links)

    def linkRect(self, link):
        return QRectF(*link)

class _MockSubRenderer:
    def __init__(self, update_result=True):
        self.update_result = update_result
        self.update_calls = []
        self.unschedule_calls = []
        self.invalidate_calls = []

    def update(self, page, device, rect, callback):
        self.update_calls.append((page, QRect(rect), callback))
        if callback:
            callback(page)
        return self.update_result

    def unschedule(self, pages, callback):
        self.unschedule_calls.append((tuple(pages), callback))

    def invalidate(self, pages):
        self.invalidate_calls.append(tuple(pages))


def test_multipage_pads_with_blank_pages():
    p1 = _MockSubPage("a1")
    p2 = _MockSubPage("a2")
    q1 = _MockSubPage("b1")

    pages = list(MultiPage.createPages([[p1, p2], [q1]]))  # type: ignore

    assert len(pages) == 2
    assert pages[0].pages[0] is p1
    assert pages[0].pages[1] is q1
    assert pages[1].pages[0] is p2
    assert pages[1].pages[1].__class__.__name__ == "BlankPage"

def test_multipage_no_padding():
    p1 = _MockSubPage("a1")
    p2 = _MockSubPage("a2")
    q1 = _MockSubPage("b1")

    pages = list(MultiPage.createPages([[p1, p2], [q1]], pad=None))  # type: ignore

    assert len(pages) == 1
    assert pages[0].pages == [p1, q1]

def test_multipage_update_size_updates_pages():
    page = MultiPage()
    page.pageWidth = 200
    page.pageHeight = 100
    page.scalePages = 1.5
    page.computedRotation = Rotate_90

    s1 = _MockSubPage("s1", w=40, h=20)
    s2 = _MockSubPage("s2", w=60, h=30)
    s2.rotation = Rotate_90
    page.pages = [s1, s2]  # type: ignore

    page.updateSize(100, 100, 2.0)

    assert s1.update_size_calls[-1] == (100, 100, 3.0)
    assert s2.update_size_calls[-1] == (100, 100, 3.0)
    assert s1.computedRotation == Rotate_90
    assert s2.computedRotation == Rotate_180

    pc = page.rect().center()
    c1 = s1.geometry().center()
    c2 = s2.geometry().center()
    # Accounts for rounding differences in centering the pages within the MultiPage
    assert abs(c1.x() - pc.x()) <= 1
    assert abs(c1.y() - pc.y()) <= 1
    assert abs(c2.x() - pc.x()) <= 1
    assert abs(c2.y() - pc.y()) <= 1

def test_multipage_non_opaque():
    page = MultiPage()
    page.opaquePages = False
    s1 = _MockSubPage("s1", x=0, y=0, w=50, h=50)
    s2 = _MockSubPage("s2", x=20, y=20, w=50, h=50)
    page.pages = [s1, s2]  # type: ignore

    visible = list(page.visiblePagesAt(QRect(0, 0, 40, 40)))

    assert [p for p, _ in visible] == [s1, s2]
    assert visible[0][1].isValid()
    assert visible[1][1].isValid()

def test_multipage_opaque():
    page = MultiPage()
    page.opaquePages = True
    top = _MockSubPage("top", x=0, y=0, w=100, h=100)
    bottom = _MockSubPage("bottom", x=0, y=0, w=100, h=100)
    page.pages = [top, bottom]  # type: ignore

    visible = list(page.visiblePagesAt(QRect(0, 0, 100, 100)))

    assert [p for p, _ in visible] == [top]

def test_multipage_text():
    page = MultiPage()
    page.opaquePages = False
    p1 = _MockSubPage("p1", x=0, y=0, w=100, h=100)
    p2 = _MockSubPage("p2", x=0, y=0, w=100, h=100)
    p1.text_value = None
    p2.text_value = "Frog"
    page.pages = [p1, p2]  # type: ignore

    result = page.text(QRect(0, 0, 50, 50))

    assert result == "Frog"

def test_multipage_link_at():
    page = MultiPage()
    page.opaquePages = False
    page.linksOnlyFirstSubPage = True
    page.width = 100
    page.height = 100
    p1 = _MockSubPage("p1", x=0, y=0, w=100, h=100)
    p2 = _MockSubPage("p2", x=0, y=0, w=100, h=100)
    l1 = [(0, 0, 10, 10)]
    l2 = [(0, 0, 20, 20)]
    p1._links = l1
    p2._links = l2
    page.pages = [p1, p2]  # type: ignore

    result = page.linksAt(QPoint(5, 5))

    assert result == l1

def test_multipage_links_in():
    page = MultiPage()
    page.opaquePages = False
    page.linksOnlyFirstSubPage = False
    p1 = _MockSubPage("p1", x=0, y=0, w=100, h=100)
    p2 = _MockSubPage("p2", x=0, y=0, w=100, h=100)
    l1 = (0, 0, 10, 10)
    l2 = (5, 5, 15, 15)
    p1._links = [l1]
    p2._links = [l2]
    page.pages = [p1, p2]  # type: ignore

    result = page.linksIn(QRect(0, 0, 20, 20))

    assert result == {l1, l2}

def test_multipage_link_rect():
    page = MultiPage()
    page.opaquePages = False
    p1 = _MockSubPage("p1", x=50, y=60, w=100, h=100)
    link = (1, 2, 11, 12)
    p1._links = [link]
    page.pages = [p1]  # type: ignore

    result = page.linkRect(link)  # type: ignore

    assert result == QRectF(51, 62, 11, 12)

def test_multipage_renderer_update_failed():
    renderer = MultiPageRenderer()
    page = MultiPage()
    page.opaquePages = False
    s1 = _MockSubPage("s1", x=0, y=0, w=40, h=40)
    s2 = _MockSubPage("s2", x=50, y=0, w=40, h=40)
    s1.renderer = _MockSubRenderer(update_result=True)
    s2.renderer = _MockSubRenderer(update_result=False)
    page.pages = [s1, s2]  # type: ignore

    result = renderer.update(page, QImage(100, 100, QImage.Format.Format_ARGB32), QRect(0, 0, 100, 100))

    assert result is False
    assert len(s1.renderer.update_calls) == 1
    assert len(s2.renderer.update_calls) == 1

# I needed to do some heavy lifting to get this test to work. It was returning a
# nasty exit code (-1073740791 (0xC0000409)) without the monkeypatching and the
# fake pixmap. I think it was trying to paint a pixmap that had been deleted.
# After a while of trying to rig it, I gave up for now. - SP
# def test_multipage_renderer_paint_behavior(monkeypatch):
#     renderer = MultiPageRenderer()
#     renderer.paperColor = QColor("green")
#     page = MultiPage()
#     page.opaquePages = False
#     top = _MockSubPage("top", x=0, y=0, w=40, h=40)
#     bottom = _MockSubPage("bottom", x=50, y=0, w=40, h=40)
#     page.pages = [top, bottom]  # type: ignore
#
#     class _FakePixmap:
#         def __init__(self, size):
#             self.size = size
#
#         def isNull(self):
#             return False
#
#         def setDevicePixelRatio(self, ratio):
#             pass
#
#     monkeypatch.setattr("qpageview.multipage.QPixmap", _FakePixmap)
#
#     combine_calls = []
#     monkeypatch.setattr(
#         renderer,
#         "combine",
#         lambda painter, pixmaps: combine_calls.append((painter, list(pixmaps)))
#     )
#
#     canvas = QImage(120, 60, QImage.Format.Format_ARGB32)
#     canvas.fill(QColor("red"))
#     painter = QPainter(canvas)
#     try:
#         renderer.paint(page, painter, QRect(0, 0, 120, 60))
#     finally:
#         painter.end()
#
#     assert len(top.paint_calls) == 1
#     assert len(bottom.paint_calls) == 1
#     assert len(combine_calls) == 1
#     assert len(combine_calls[0][1]) == 2
#     assert canvas.pixelColor(110, 30) == QColor("green")

def test_multipage_renderer_image_combines():
    renderer = MultiPageRenderer()
    renderer.paperColor = QColor("green")
    page = MultiPage()
    page.opaquePages = False
    page.pageWidth = 100
    page.pageHeight = 100
    page.width = 100
    page.height = 100
    page.dpi = 100.0
    s1 = _MockSubPage("s1", x=0, y=0, w=50, h=50)
    page.pages = [s1]  # type: ignore

    img = renderer.image(page, QRect(0, 0, 100, 100), 100, 100, QColor("green"))

    assert isinstance(img, QImage)
    assert img.width() == 100
    assert img.height() == 100
    assert len(s1.image_calls) == 1

def test_multipage_renderer_unschedule_and_invalidate():
    renderer = MultiPageRenderer()
    page = MultiPage()
    page.opaquePages = False
    s1 = _MockSubPage("s1")
    s2 = _MockSubPage("s2")
    r1 = _MockSubRenderer()
    r2 = _MockSubRenderer()
    s1.renderer = r1
    s2.renderer = r2
    page.pages = [s1, s2]  # type: ignore

    renderer.unschedule([page], lambda _: None)
    renderer.invalidate([page])

    assert len(r1.unschedule_calls) == 1
    assert len(r2.unschedule_calls) == 1
    assert len(r1.invalidate_calls) == 1
    assert len(r2.invalidate_calls) == 1

def test_multipage_renderer_callback():
    called = []

    def original(p):
        called.append(p)

    page = object()
    cb = CallBack(original, page)  # type: ignore

    assert hash(cb) == hash(original)
    cb(object())  # type: ignore
    assert called == [page]

def test_multipage_renderer_callback_equality():
    def original(_):
        pass

    p1 = object()
    p2 = object()
    cb1 = CallBack(original, p1)  # type: ignore
    cb2 = CallBack(cb1, p1)  # type: ignore

    assert cb1 is cb2
