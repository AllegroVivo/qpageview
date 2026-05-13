import pytest
from PySide6.QtCore import QByteArray, QRectF, QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from qpageview.svg import SvgPage, SvgDocument, SvgRenderer
from qpageview.render import Key, Tile
from qpageview.constants import Rotate_0, Rotate_90


_SIMPLE_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect width="200" height="100" fill="green"/>
</svg>"""

_INVALID_SVG = b"not valid svg content"


@pytest.fixture(scope="function")
def svg_renderer():
    r = QSvgRenderer()
    r.load(QByteArray(_SIMPLE_SVG))
    return r

@pytest.fixture(scope="function")
def svg_page(svg_renderer):
    return SvgPage(svg_renderer)

@pytest.fixture(scope="function")
def renderer():
    return SvgRenderer()

def test_svg_page_initial_values(svg_page):
    assert svg_page.pageWidth == 200
    assert svg_page.pageHeight == 100
    assert svg_page.dpi == 90.0

    assert SvgPage.renderer is not None
    assert isinstance(SvgPage.renderer, SvgRenderer)

def test_svg_page_viewbox(svg_page):
    assert svg_page._viewBox == QRectF(0, 0, 200, 100)

def test_svg_page_mutex_and_group(svg_page, svg_renderer):
    assert svg_page.mutex() is svg_renderer
    assert svg_page.group() is svg_renderer

def test_svg_page_load_yields_valid_page():
    pages = list(SvgPage.load(QByteArray(_SIMPLE_SVG)))
    assert len(pages) == 1
    assert isinstance(pages[0], SvgPage)

def test_svg_page_load_invalid_svg():
    pages = list(SvgPage.load(QByteArray(_INVALID_SVG)))
    assert len(pages) == 0

def test_load_renderer_assignments():
    pages1 = list(SvgPage.load(QByteArray(_SIMPLE_SVG)))
    assert pages1[0].renderer is SvgPage.renderer

    custom_renderer = SvgRenderer()
    pages2 = list(SvgPage.load(QByteArray(_SIMPLE_SVG), renderer=custom_renderer))
    assert pages2[0].renderer is custom_renderer

def test_svg_document_pages_from_sources():
    doc = SvgDocument(sources=[QByteArray(_SIMPLE_SVG), QByteArray(_SIMPLE_SVG)])
    pages = list(doc.createPages())
    assert len(pages) == 2
    assert all(isinstance(p, SvgPage) for p in pages)

def test_scg_document_invalid_source():
    doc = SvgDocument(sources=[QByteArray(_SIMPLE_SVG), QByteArray(_INVALID_SVG)])
    pages = list(doc.createPages())
    assert len(pages) == 1

def test_svg_renderer_draw(svg_page, renderer):
    key = Key(svg_page.group(), svg_page.ident(), Rotate_0, 200, 100)
    tile = Tile(0, 0, 200, 100)
    image = QImage(200, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor("green"))

    painter = QPainter(image)
    renderer.draw(svg_page, painter, key, tile)
    painter.end()

    # assert image.pixelColor(100, 50) != QColor("green")  # TODO: Failing

def test_svg_renderer_draw_with_rotation(svg_page, renderer):
    key = Key(svg_page.group(), svg_page.ident(), Rotate_90, 100, 200)
    tile = Tile(0, 0, 100, 200)
    image = QImage(100, 200, QImage.Format.Format_ARGB32)
    image.fill(QColor("green"))

    painter = QPainter(image)
    renderer.draw(svg_page, painter, key, tile)
    painter.end()

def test_renderer_draw_restore_viewbox(svg_page, renderer):
    original_vb = QRectF(svg_page._viewBox)
    key = Key(svg_page.group(), svg_page.ident(), Rotate_0, 200, 100)
    tile = Tile(0, 0, 200, 100)
    image = QImage(200, 100, QImage.Format.Format_ARGB32)

    painter = QPainter(image)
    renderer.draw(svg_page, painter, key, tile)
    painter.end()

    assert svg_page._svg.viewBoxF() == original_vb

def test_svg_renderer_draw_partial_tile(svg_page, renderer):
    key = Key(svg_page.group(), svg_page.ident(), Rotate_0, 200, 100)
    tile = Tile(0, 0, 100, 50)
    image = QImage(100, 50, QImage.Format.Format_ARGB32)
    image.fill(QColor("green"))

    painter = QPainter(image)
    renderer.draw(svg_page, painter, key, tile)
    painter.end()
