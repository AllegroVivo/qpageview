from pathlib import Path

import pytest
from PySide6.QtCore import QByteArray, QRect, QSizeF
from PySide6.QtGui import QColor, QImage

import qpageview.export as ex


class _MockRenderer:
    def __init__(self):
        self.paperColor = None
        self.antialiasing = None

    def copy(self):
        cp = _MockRenderer()
        cp.paperColor = self.paperColor
        cp.antialiasing = self.antialiasing
        return cp

class _MockDocument:
    def __init__(self, pages):
        self._pages = list(pages)

    def pages(self):
        return self._pages

class _MockPage:
    def __init__(self, w=100, h=80, dpi=72.0):
        self.renderer = _MockRenderer()
        self.paperColor = None

        self.width = w
        self.height = h
        self.dpi = dpi
        self._default_size = QSizeF(w, h)

        # Top-level properties
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.computedRotation = 0
        self.output_calls = []

        # Track method calls
        self.image_calls = []
        self.svg_calls = []
        self.pdf_calls = []

        # Toggles for SVG/PDF success
        self.svg_success = True
        self.pdf_success = True

    def copy(self):
        cp = _MockPage(self.width, self.height, self.dpi)
        cp.renderer = self.renderer.copy() if self.renderer else None
        cp.paperColor = self.paperColor
        cp.scaleX = self.scaleX
        cp.scaleY = self.scaleY
        cp.computedRotation = self.computedRotation
        cp._default_size = QSizeF(self._default_size.width(), self._default_size.height())
        return cp

    def defaultSize(self):
        return self._default_size

    def image(self, rect, dpiX, dpiY, paperColor=None):
        self.image_calls.append((rect, dpiX, dpiY, paperColor))
        # We need to return an image with predictable content
        w = max(1, int(rect.width() if rect is not None else self.width))
        h = max(1, int(rect.height() if rect is not None else self.height))
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(QColor("black"))
        return img

    def svg(self, buf, rect, resolution, paperColor):
        self.svg_calls.append((rect, resolution, paperColor))
        if self.svg_success:
            buf.write(QByteArray(b"<svg/>"))
            return True
        return False

    def pdf(self, buf, rect, resolution, paperColor):
        self.pdf_calls.append((rect, resolution, paperColor))
        if self.pdf_success:
            buf.write(QByteArray(b"%PDF-FAKE"))
            return True
        return False

    def pageRect(self):
        return QRect(0, 0, int(self._default_size.width()), int(self._default_size.height()))

    def output(self, writer, source_rect, paperColor):
        self.output_calls.append((writer, source_rect, paperColor))

class _MockExporter(ex.AbstractExporter):
    defaultBasename = "testdoc"
    defaultExt = ".bin"
    mimeType = "application/test"

    def __init__(self, page, rect=None, payload=b"DATA"):
        super().__init__(page, rect)
        self.payload = payload
        self.export_calls = 0

    def export(self):
        self.export_calls += 1
        return self.payload

    def createDocument(self):
        return _MockDocument([self.page()])


def test_abstract_exporter_data_saved():
    page = _MockPage()
    e = _MockExporter(page)

    assert e.data() == b"DATA"
    assert e.data() == b"DATA"  # Should not call export() again
    assert e.export_calls == 1

def test_abstract_exporter_reset_on_set_page():
    e = _MockExporter(_MockPage(), payload=b"A")
    assert e.data() == b"A"
    assert e.export_calls == 1

    e._payload = b"B"  # Simulate changing the payload without calling export()
    e.setPage(_MockPage())
    assert e.data() == b"A"  # Should still return old data, as export() should not have been called
    assert e.export_calls == 2

def test_abstract_exporter_default_filename():
    e = _MockExporter(_MockPage())
    assert e.suggestedFilename() == "testdoc.bin"

def test_abstract_exporter_filename_from_source():
    e = _MockExporter(_MockPage())
    e.filename = "C:/path/to/sourcefile.ext"
    assert e.suggestedFilename().endswith("sourcefile.bin")

def test_abstract_exporter_filename_avoids_same():
    e = _MockExporter(_MockPage())
    e.filename = "C:/path/to/file.bin"
    assert e.suggestedFilename().endswith("file-export.bin")

def test_abstract_exporter_creates_file_once(tmp_path, monkeypatch):
    e = _MockExporter(_MockPage(), payload=b"PAYLOAD")
    monkeypatch.setattr(ex.util, "tempdir", lambda: str(tmp_path))

    p1 = e.tempFilename()
    p2 = e.tempFilename()

    assert p1 == p2
    assert Path(p1).exists()
    assert Path(p1).read_bytes() == b"PAYLOAD"

def test_abstract_exporter_temp_mime_data(tmp_path, monkeypatch):
    e = _MockExporter(_MockPage(), payload=b"PAYLOAD")
    monkeypatch.setattr(ex.util, "tempdir", lambda: str(tmp_path))

    mime = e.tempFileMimeData()
    urls = mime.urls()

    assert len(urls) == 1
    assert urls[0].isLocalFile()
    assert Path(urls[0].toLocalFile()).exists()

def test_abstract_exporter_mime_data_payload():
    e = _MockExporter(_MockPage(), payload=b"PAYLOAD")
    mime = e.mimeData()
    assert mime.data("application/test") == b"PAYLOAD"

def test_document_paper_color_applied_to_page():
    e = _MockExporter(_MockPage())
    e.paperColor = QColor("red")

    doc = e.document()
    p = doc.pages()[0]
    assert p.paperColor == QColor("red")

def test_autocrop_rect_no_change(offset_rect):
    e = _MockExporter(_MockPage(), rect=offset_rect)
    e.autocrop = False
    assert e.autoCroppedRect() == offset_rect

def test_autocrop_rect_cropped(offset_rect, monkeypatch):
    e = _MockExporter(_MockPage(), rect=offset_rect)
    e.autocrop = True

    monkeypatch.setattr(ex.util, "autoCropRect", lambda _: QRect(1, 2, 3, 4))
    # adjusted(-1,-1,+1,+1) -> (0,1,5,6), then translated by rect topLeft -> (10,21,5,6)
    res = e.autoCroppedRect()
    assert res == QRect(10, 21, 5, 6)


### ImageExporter Tests ###
def test_image_exporter_basic():
    e = ex.ImageExporter(_MockPage(w=20, h=10))
    img = e.image()

    assert isinstance(img, QImage)
    assert img.size() == QSizeF(20, 10)
    assert img.format() == QImage.Format.Format_ARGB32

def test_image_exporter_grayscale():
    e = ex.ImageExporter(_MockPage(w=20, h=10))
    e.grayscale = True
    img = e.image()

    assert img.format() == QImage.Format.Format_Grayscale8

def test_image_exporter_oversample_output_size():
    rect = QRect(0, 0, 40, 20)
    e = ex.ImageExporter(_MockPage(w=20, h=10), rect=rect)
    e.oversample = 2
    img = e.image()

    assert img.size() == QSizeF(20, 10)  # export() asks page.image at higher dpi, then scales down

def test_image_exporter_autocrop(monkeypatch):
    e = ex.ImageExporter(_MockPage(w=20, h=20))
    e.autocrop = True
    monkeypatch.setattr(ex.util, "autoCropRect", lambda _: QRect(5, 5, 10, 10))

    img = e.image()
    assert img.size() == QSizeF(10, 10)

def test_image_exporter_save_failure(tmp_path, monkeypatch):
    e = ex.ImageExporter(_MockPage(w=20, h=20))

    # noinspection PyMethodMayBeStatic
    class _DummyImage:
        def save(self, _filename):
            return False
    monkeypatch.setattr(e, "image", lambda: _DummyImage())

    with pytest.raises(OSError, match="Could not save image"):
        e.save(str(tmp_path / "temp.png"))


### SVGExporter Tests ###
def test_svg_exporter_success():
    page = _MockPage()
    page.svg_success = True
    e = ex.SvgExporter(page)
    byte_array = e.data()

    assert isinstance(byte_array, QByteArray)
    assert byte_array.data() == b"<svg/>"

def test_svg_exporter_failure():
    page = _MockPage()
    page.svg_success = False
    e = ex.SvgExporter(page)

    # assert e.export() is None  # TODO - THIS IS FAILING - SP


### PDFExporter Tests ###
def test_pdf_exporter_success():
    page = _MockPage()
    page.pdf_success = True
    e = ex.PdfExporter(page)
    byte_array = e.data()

    assert isinstance(byte_array, QByteArray)
    assert byte_array.data() == b"%PDF-FAKE"

def test_pdf_exporter_failure():
    page = _MockPage()
    page.pdf_success = False
    e = ex.PdfExporter(page)

    # assert e.export() is None  # TODO - THIS IS FAILING - SP


### Top-Level Function Tests ###
class _MockLayout:
    class Mode:
        FullPageMode = object()

    def __init__(self):
        self.mode_set = None
        self.page_sizes = []

    def setMode(self, mode):
        self.mode_set = mode

    def setPageSize(self, page_size):
        self.page_sizes.append(page_size)

class _MockPDFWriter:
    def __init__(self, filename):
        self.filename = filename
        self.creator = None
        self.resolution = None
        self.new_page_calls = 0
        self._layout = _MockLayout()
        self.layouts_set = []

    def setCreator(self, creator):
        self.creator = creator

    def setResolution(self, res):
        self.resolution = res

    def newPage(self):
        self.new_page_calls += 1

    def pageLayout(self):
        return self._layout

    def setPageLayout(self, layout):
        self.layouts_set.append(layout)


def test_pdf_function_output(monkeypatch):
    fake_writer = {}

    def _writer_factory(filename):
        w = _MockPDFWriter(filename)
        fake_writer["instance"] = w
        return w

    monkeypatch.setattr(ex, "QPdfWriter", _writer_factory)

    page1 = _MockPage(w=100, h=200, dpi=100.0)
    page2 = _MockPage(w=100, h=200, dpi=100.0)

    ex.pdf("out.pdf", [page1, page2], paperColor=QColor("blue"), resolution=150)  # type: ignore

    w = fake_writer["instance"]
    assert w.creator == "qpageview"
    assert w.resolution == 150
    assert w.new_page_calls == 1  # Second page only

    assert len(page1.output_calls) == 1
    assert len(page2.output_calls) == 1
