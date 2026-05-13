import pytest

from PySide6.QtGui import QImage, QColor

from qpageview.cache import ImageCache, ImageEntry
from qpageview.render import Key, Tile
from qpageview.constants import Rotate_0, Rotate_90


def _make_image(w=10, h=10, color=QColor("white")) -> QImage:
    image = QImage(w, h, QImage.Format.Format_ARGB32)
    image.fill(color)
    return image

def _key(group, ident, rotation=Rotate_0, width=100, height=200) -> Key:
    return Key(group, ident, rotation, width, height)

def _tile(x=0, y=0, w=100, h=200) -> Tile:
    return Tile(x, y, w, h)


### ImageEntry Tests ###
def test_image_entry():
    image = _make_image()
    entry = ImageEntry(image)

    assert entry.image == image
    assert entry.bcount == image.sizeInBytes()
    assert entry.time > 0


### ImageCache Tests ###
class _GroupObject:
    """A simple object to use as a group key in tests."""
    __slots__ = ("__weakref__",)

@pytest.fixture(scope="function")
def cache():
    return ImageCache()

@pytest.fixture(scope="function")
def group():
    """Return a unique group object for testing. Used as a key in the cache."""
    return _GroupObject()

def test_cache_starts_empty(cache):
    assert cache.currentsize == 0

def test_add_and_retrieve_tile(cache, group):
    key = _key(group, "Page1")
    tile = _tile()
    image = _make_image()

    cache.addtile(key, tile, image)

    tileset = cache.tileset(key)
    assert tile in tileset
    assert tileset[tile].image is image
    assert cache.currentsize == image.sizeInBytes()

def test_replace_tile(cache, group):
    key = _key(group, "Page1")
    tile = _tile()
    image1 = _make_image(10, 10)
    image2 = _make_image(20, 20)

    cache.addtile(key, tile, image1)
    cache.addtile(key, tile, image2)

    assert cache.currentsize == image2.sizeInBytes()
    assert cache.tileset(key)[tile].image is image2

def test_unknown_key(cache, group):
    key = _key(group, "Unknown")
    assert cache.tileset(key) == {}

def test_clear_removes_all(cache, group):
    key = _key(group, "Page1")

    cache.addtile(key, _tile(), _make_image())
    cache.clear()

    assert cache.currentsize == 0
    assert cache.tileset(key) == {}

def test_invalidate_removes_page(cache, group):
    # noinspection PyMethodMayBeStatic
    class MockPage:
        def group(self): return group
        def ident(self): return "Page1"

    key1 = _key(group, "Page1")
    key2 = _key(group, "Page2")

    cache.addtile(key1, _tile(), _make_image())
    cache.addtile(key2, _tile(), _make_image())

    cache.invalidate(MockPage())  # type: ignore

    assert cache.tileset(key1) == {}
    assert cache.tileset(key2) != {}  # Should still be there

def test_invalidate_unknown_page(cache, group):
    # noinspection PyMethodMayBeStatic
    class MockPage:
        def group(self): return group
        def ident(self): return "Unknown"

    key = _key(group, "Page1")
    cache.addtile(key, _tile(), _make_image())

    cache.invalidate(MockPage())  # type: ignore

    assert cache.tileset(key) != {}

def test_purge_respects_maxsize(cache, group):
    img = _make_image(200, 200)
    cache.maxsize = img.sizeInBytes() - 1  # Set maxsize just below the image size

    key1 = _key(group, "Page1")
    key2 = _key(group, "Page2")

    cache.addtile(key1, _tile(), img)
    assert cache.currentsize == img.sizeInBytes()

    cache.addtile(key2, _tile(), img)  # This should trigger purge
    assert cache.currentsize <= cache.maxsize + img.sizeInBytes()
    assert cache.tileset(key1) == {}  # Old tile should be purged
    assert cache.tileset(key2) != {}  # New tile should be there

def test_closest_unknown_group(cache, group):
    key = _key(group, "Unknown")
    assert cache.closest(key) == []

def test_closest_different_widths(cache, group):
    key_100 = _key(group, "Page1", width=100, height=200)
    key_200 = _key(group, "Page1", width=200, height=400)

    cache.addtile(key_100, _tile(w=100, h=200), _make_image(100, 200))
    cache.addtile(key_200, _tile(w=200, h=400), _make_image(200, 400))

    closest = cache.closest(key_100)
    widths = [w for w, h, tileset in closest]

    assert 200 in widths
    assert 100 not in widths  # Exact match should not be included

def test_closest_sorted_by_proximity(cache, group):
    key_target = _key(group, "Page1", width=100)
    key_50 = _key(group, "Page1", width=50, height=100)
    key_90 = _key(group, "Page1", width=90, height=180)
    key_200 = _key(group, "Page1", width=200, height=400)

    cache.addtile(key_50, _tile(), _make_image())
    cache.addtile(key_90, _tile(), _make_image())
    cache.addtile(key_200, _tile(), _make_image())

    closest = cache.closest(key_target)
    widths = [w for w, h, _ in closest]

    assert widths == [90, 200]  # Should be sorted by proximity to target width
