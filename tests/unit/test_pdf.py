import platform

import pytest
from PySide6.QtCore import QByteArray, QRect, QRectF, QSizeF, QBuffer, QUrl
from PySide6.QtGui import QImage, QColor, QPainter, QTransform
from PySide6.QtPdf import QPdfDocument, QPdfDocumentRenderOptions

import qpageview.pdf as pdfmod
from qpageview.constants import Rotate_0, Rotate_90
from qpageview.pdf import PdfRenderer, PdfDocument, Link, load
from qpageview.render import Key, Tile


class _MockSelection:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

class _MockPdfDocument(QPdfDocument):
    class Error:
        None_ = 0
        DataNotYetAvailable = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._error = self.Error.None_
        self._loaded = None
        self._selection_calls = []
        self._render_calls = []

    def load(self, source):
        self._loaded = source
        return self._error

    def error(self):
        return self._error

    def pageCount(self):
        return 3

    def pagePointSize(self, page):
        return QSizeF(200 + page, 300 + page)

    def getSelection(self, page, topLeft, bottomRight):
        self._selection_calls.append((page, topLeft, bottomRight))
        return _MockSelection("Selected text!")

    def render(self, page, renderSize, renderOptions=...):
        self._render_calls.append((page, renderSize, renderOptions))
        image = QImage(max(1, renderSize.width()), max(1, renderSize.height()), QImage.Format.Format_ARGB32)
        image.fill(QColor("green"))
        return image

class _MockLinkModel:
    def __init__(self, document=None, page=0):
        self.page_role = pdfmod.QPdfLinkModel.Role.Page.value
        self.url_role = pdfmod.QPdfLinkModel.Role.Url.value
        self.rect_role = pdfmod.QPdfLinkModel.Role.Rectangle.value

        self._rows = [
            {
                self.page_role: 0,
                self.url_role: QUrl("https://example.org"),
                self.rect_role: QRectF(10, 20, 30, 40),
            },
            {
                self.page_role: -1,
                self.url_role: QUrl("file:///c:/docs/readme.txt"),
                self.rect_role: QRectF(1, 2, 3, 4),
            },
        ]

    def rowCount(self):
        return len(self._rows)

    def index(self, row, _col, _parent):
        return row

    def data(self, index, role):
        return self._rows[index][role]

class _MockPage:
    def __init__(self, document, page_number):
        self.document = document
        self.pageNumber = page_number
        self.paperColor = None
        self.dpi = 72.0
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.rotation = 0
        self.computedRotation = 0

    def pageSize(self):
        return QSizeF(100, 200)


def test_load_qpdfdocument(monkeypatch):
    doc = _MockPdfDocument()
    monkeypatch.setattr(pdfmod, "QPdfDocument", _MockPdfDocument)

    result = load(doc)  # type: ignore
    assert result is doc

def test_load_string_failure(monkeypatch):
    class _FailingDoc(_MockPdfDocument):
        def __init__(self, _=None):
            super().__init__()
            self._error = self.Error.DataNotYetAvailable

    monkeypatch.setattr(pdfmod, "QPdfDocument", _FailingDoc)

    result = load("somefile.pdf")
    assert result is None

def test_load_string_success(monkeypatch):
    monkeypatch.setattr(pdfmod, "QPdfDocument", _MockPdfDocument)

    result = load("file_exists.pdf")

    assert result is not None
    assert result._loaded == "file_exists.pdf"

def test_load_qbytearray_fail(monkeypatch):
    class _FailingDoc(_MockPdfDocument):
        def __init__(self, _=None):
            super().__init__()
            self._error = self.Error.DataNotYetAvailable

    monkeypatch.setattr(pdfmod, "QPdfDocument", _FailingDoc)
    result = load(QByteArray(b"Fake PDF data"))

    assert result is None

def test_load_qbytearray_success(monkeypatch):
    monkeypatch.setattr(pdfmod, "QPdfDocument", _MockPdfDocument)
    result = load(QByteArray(b"%PDF-1.7\n..."))

    assert result is not None
    assert isinstance(result._loaded, QBuffer)

def test_pdf_document_load_fails(monkeypatch):
    monkeypatch.setattr(pdfmod, "load", lambda _: None)
    doc = PdfDocument("broken.pdf")

    result = doc.document()

    assert result is False

def test_pdf_document_create_pages(monkeypatch):
    monkeypatch.setattr(pdfmod, "load", lambda _: _MockPdfDocument())
    doc = PdfDocument("file_exists.pdf")

    pages = list(doc.createPages())

    assert len(pages) == 3
    assert pages[0].pageNumber == 0
    assert pages[1].pageNumber == 1
    assert pages[2].pageNumber == 2

def test_pdf_document_invalidate(monkeypatch):
    pdf_doc = _MockPdfDocument()
    monkeypatch.setattr(pdfmod, "load", lambda _: pdf_doc)
    doc = PdfDocument("a_totally_real_file.pdf")

    first = doc.document()
    doc.invalidate()
    second = doc.document()

    assert first is pdf_doc
    assert second is pdf_doc

def test_pdf_link_targets(monkeypatch):
    monkeypatch.setattr(pdfmod, "QPdfDocument", _MockLinkModel)
    lm = _MockLinkModel()
    point_size = QSizeF(200, 400)

    internal = Link(lm, 0, point_size)  # type: ignore
    external = Link(lm, 1, point_size)  # type: ignore

    assert internal.targetPage == 1
    assert internal.isExternal is True
    assert internal.url == "https://example.org"
    assert internal.fileName == ""

    assert external.targetPage == -1
    assert external.isExternal is True
    assert external.fileName == "readme.txt"

def test_pdf_link_normalizes_url(monkeypatch):
    monkeypatch.setattr(pdfmod, "QPdfDocument", _MockLinkModel)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    lm = _MockLinkModel()
    lm._rows[1][lm.url_role] = QUrl("file:///C:/docs/readme.txt")
    point_size = QSizeF(100, 100)

    link = Link(lm, 1, point_size)  # type: ignore

    assert link.url.startswith("file://")
    assert "C:" in link.url

def test_pdf_renderer_full_page_tile():
    renderer = PdfRenderer()

    tiles = list(renderer.tiles(640, 480))

    assert len(tiles) == 1
    assert tiles[0] == Tile(0, 0, 640, 480)

def test_pdf_renderer_draw_calls(monkeypatch):
    doc = _MockPdfDocument()
    page = _MockPage(doc, 2)  # type: ignore
    renderer = PdfRenderer()
    renderer.antialiasing = True

    img = QImage(200, 400, QImage.Format.Format_ARGB32)
    img.fill(QColor("green"))
    painter = QPainter(img)

    key = Key(group="g", ident=2, rotation=Rotate_0, width=100, height=200)
    tile = Tile(0, 0, 100, 200)

    renderer.draw(page, painter, key, tile, QColor("red"))  # type: ignore
    painter.end()

    assert len(doc._render_calls) == 1
    called_page, render_size, render_options = doc._render_calls[0]
    assert called_page == 2
    assert render_size == QSizeF(200, 400)
    assert isinstance(render_options, QPdfDocumentRenderOptions)

def test_pdf_renderer_non_antialias_flags():
    doc = _MockPdfDocument()
    page = _MockPage(doc, 0)  # type: ignore
    renderer = PdfRenderer()
    renderer.antialiasing = False

    img = QImage(120, 240, QImage.Format.Format_ARGB32)
    painter = QPainter(img)

    key = Key(group="g", ident=0, rotation=Rotate_0, width=100, height=200)
    tile = Tile(0, 0, 100, 200)

    renderer.draw(page, painter, key, tile, None)  # type: ignore
    painter.end()

    _, _, options = doc._render_calls[0]
    flags = options.renderFlags()
    assert flags != QPdfDocumentRenderOptions.RenderFlag(0)

def test_pdf_renderer_tile_crop():
    doc = _MockPdfDocument()
    page = _MockPage(doc, 1)  # type: ignore
    renderer = PdfRenderer()
    renderer.antialiasing = True

    img = QImage(200, 200, QImage.Format.Format_ARGB32)
    painter = QPainter(img)

    key = Key(group="g", ident=1, rotation=Rotate_0, width=100, height=100)
    tile = Tile(10, 10, 30, 40)

    renderer.draw(page, painter, key, tile, None)  # type: ignore
    painter.end()

    assert len(doc._render_calls) == 1

def test_pdf_renderer_draw_rotated_key():
    doc = _MockPdfDocument()
    page = _MockPage(doc, 0)  # type: ignore
    renderer = PdfRenderer()

    img = QImage(300, 300, QImage.Format.Format_ARGB32)
    painter = QPainter(img)

    key = Key(group="g", ident=0, rotation=Rotate_90, width=100, height=200)
    tile = Tile(0, 0, 100, 200)

    renderer.draw(page, painter, key, tile, None)  # type: ignore
    painter.end()

    assert len(doc._render_calls) == 1
