import pytest
from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QColor, QImage, QPainter

import qpageview.render as rendermod
from qpageview.constants import Rotate_180, Rotate_0
from qpageview.render import AbstractRenderer, Key, Tile


class _MockCacheEntry:
    def __init__(self, image):
        self.image = image
        self.time = 0.0

class _MockCache:
    def __init__(self):
        self._tilesets = {}
        self.closest_result = []
        self.added = []
        self.invalidated = []

    def tileset(self, key):
        return self._tilesets.setdefault(key, {})

    def closest(self, _):
        return self.closest_result

    def addtile(self, key, tile, image):
        self.added.append((key, tile, image))
        self.tileset(key)[tile] = _MockCacheEntry(image)

    def invalidate(self, page):
        self.invalidated.append(page)

class _MockPage:
    def __init__(self):
        self.width = 200
        self.height = 100
        self.computedRotation = 0
        self.paperColor = None
        self.dpi = 100.0
        self._group = "group"
        self._ident = "ident"
        self._mutex = None
        self.default_size = QRectF(0, 0, 200, 100)

    def group(self):
        return self._group

    def ident(self):
        return self._ident

    def mutex(self):
        return self._mutex

    def defaultSize(self):
        return self.default_size

class _MockDevice:
    def __init__(self, ratio=1.0):
        self.ratio = ratio

    def devicePixelRatioF(self):
        return self.ratio

    def devicePixelRatio(self):
        return int(self.ratio)

class _MockRenderer(AbstractRenderer):
    def __init__(self, cache=None):
        super().__init__(cache=cache)
        self.draw_calls = []
        self.render_calls = []
        self.scheduled = []
        self._jobs = {}

    def draw(self, page, painter, key, tile, paperColor=None):
        self.draw_calls.append((page, key, tile, paperColor))
        painter.fillRect(QRect(0, 0, tile.w, tile.h), QColor("green"))

    def render(self, page, key, tile, paperColor=None):
        self.render_calls.append((page, key, tile, paperColor))
        return super().render(page, key, tile, paperColor)

    def schedule(self, page, key, tiles, callback):
        self.scheduled.append((page, key, list(tiles), callback))


@pytest.fixture(scope="function")
def renderer():
    return _MockRenderer(cache=_MockCache())  # type: ignore

@pytest.fixture(scope="function")
def page():
    return _MockPage()

def test_renderer_key(page):
    page.width = 123
    page.height = 45
    page.computedRotation = Rotate_180

    key = AbstractRenderer.key(page, 1.5)  # type: ignore

    assert key == Key("group", "ident", 2, 184, 67)

def test_renderer_return_small_dimensions(renderer):
    tiles = list(renderer.tiles(200, 100))

    assert tiles == [Tile(0, 0, 200, 100)]

def test_renderer_return_large_dimensions(renderer):
    tiles = list(renderer.tiles(5000, 3500))

    assert len(tiles) > 1
    assert sum(t.w for t in tiles if t.y == 0) == 5000

    max_y = max(t.y for t in tiles)
    bottom_row = [t for t in tiles if t.y == max_y]
    assert max(t.h for t in bottom_row) <= renderer.MAX_TILE_HEIGHT

def test_renderer_map():
    key = Key("group", "ident", Rotate_0, 200, 100)
    box = QRectF(10, 20, 400, 200)

    m = AbstractRenderer.map(key, box)
    mapped = m.mapRect(QRectF(0, 0, 200, 100))

    assert mapped.x() == pytest.approx(10)
    assert mapped.y() == pytest.approx(20)
    assert mapped.width() == pytest.approx(400)
    assert mapped.height() == pytest.approx(200)

def test_renderer_image(renderer, page):
    rect = QRectF(0, 0, 100, 50)

    image = renderer.image(page, rect, 100, 100, QColor("green"))  # type: ignore

    assert isinstance(image, QImage)
    assert len(renderer.render_calls) == 1
    _, key, tile, _ = renderer.render_calls[0]
    assert key.group == "group"
    assert key.ident == "ident"
    assert tile.w > 0
    assert tile.h > 0

def test_renderer_render(renderer, page):
    page.paperColor = QColor("green")

    image = renderer.render(page, Key("group", "ident", Rotate_0, 20, 10), Tile(0, 0, 20, 10))  # type: ignore

    assert image.pixelColor(0, 0) == QColor("green")

def test_renderer_info(renderer, page):
    key = renderer.key(page, 1.0)  # type: ignore
    existing_tile = Tile(0, 0, page.width, page.height)
    cached_img = QImage(page.width, page.height, QImage.Format.Format_ARGB32)
    renderer.cache.tileset(key)[existing_tile] = _MockCacheEntry(cached_img)  # type: ignore

    info = renderer.info(page, _MockDevice(1.0), QRect(0, 0, page.width, page.height))  # type: ignore

    assert info.key == key
    assert len(info.images) == 1
    assert info.images[0][0] == existing_tile
    assert info.missing == []

def test_renderer_update(renderer, page):
    key = renderer.key(page, 1.0)  # type: ignore
    tile = Tile(0, 0, page.width, page.height)
    renderer.cache.tileset(key)[tile] = _MockCacheEntry(QImage(page.width, page.height, QImage.Format.Format_ARGB32))  # type: ignore

    result = renderer.update(page, _MockDevice(1.0), QRect(0, 0, page.width, page.height), None)  # type: ignore

    assert result is True
    assert renderer.scheduled == []

def test_renderer_update_tiles_missing(renderer, page):
    result  = renderer.update(page, _MockDevice(1.0), QRect(0, 0, page.width, page.height), None)  # type: ignore

    assert result is False
    assert len(renderer.scheduled) == 1

def test_renderer_paint_draws_cached(renderer, page):
    key = renderer.key(page, 1.0)  # type: ignore
    tile = Tile(0, 0, page.width, page.height)
    cached_img = QImage(page.width, page.height, QImage.Format.Format_ARGB32)
    cached_img.fill(QColor("green"))
    renderer.cache.tileset(key)[tile] = _MockCacheEntry(cached_img)  # type: ignore

    canvas = QImage(page.width, page.height, QImage.Format.Format_ARGB32)
    canvas.fill(QColor("black"))
    painter = QPainter(canvas)
    renderer.paint(page, painter, QRect(0, 0, page.width, page.height))  # type: ignore
    painter.end()

    assert canvas.pixelColor(10, 10) == QColor("green")

def test_renderer_paint_fills_background(renderer, page):
    renderer.cache.closest_result = []

    canvas = QImage(page.width, page.height, QImage.Format.Format_ARGB32)
    canvas.fill(QColor("black"))
    painter = QPainter(canvas)
    renderer.paint(page, painter, QRect(0, 0, page.width, page.height))  # type: ignore
    painter.end()

    assert canvas.pixelColor(5, 5) == renderer.paperColor

def test_renderer_unschedule(monkeypatch, renderer, page):
    key = Key(page.group(), page.ident(), page.computedRotation, page.width, page.height)
    tile = Tile(0, 0, 10, 10)
    callback = lambda _: None

    class _Job:
        def __init__(self):
            self.callbacks = {callback}
            self.running = False
            self.finalize = object()
            self.work = object()

    rendermod._jobs[(key, tile)] = _Job()  # type: ignore

    renderer.unschedule([page], callback)  # type: ignore

    assert (key, tile) not in rendermod._jobs

def test_renderer_invalidate(renderer, page):
    renderer.invalidate([page])  # type: ignore

    assert renderer.cache.invalidated == [page]
