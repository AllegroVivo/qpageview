from pathlib import Path

import pytest
from PySide6.QtCore import Qt, QObject, Signal, QRect
from PySide6.QtGui import QTransform, QImage, QColor
from pytestqt.plugin import qapp

from qpageview.constants import Rotate_0, Rotate_90, Rotate_180, Rotate_270
from qpageview.util import (
    rotate, Point, align, alignrect, clamp, clamp_int32,
    signalsBlocked, autoCropRect, tempdir
)


### rotate Tests ###
def _map_points(t, points):
    return [t.map(p) for p in points]

@pytest.mark.parametrize("rotation, expected", [
    (Rotate_0, [Point(0, 0), Point(10, 0), Point(0, 20)]),
    (Rotate_90, [Point(20, 0), Point(20, 10), Point(0, 0)]),
    (Rotate_180, [Point(10, 20), Point(0, 20), Point(10, 0)]),
    (Rotate_270, [Point(0, 10), Point(0, 0), Point(20, 10)]),
])
def test_rotate_source_space(rotation, expected, identity_transform):
    rotate(identity_transform, rotation, width=10, height=20, dest=False)
    points = [Point(0, 0), Point(10, 0), Point(0, 20)]
    got = _map_points(identity_transform, points)
    assert got == expected

def test_rotate_dest_true_90_uses_dest_dimensions():
    t_dest = QTransform()
    rotate(t_dest, Rotate_90, width=20, height=10, dest=True)

    t_src = QTransform()
    rotate(t_src, Rotate_90, width=10, height=20, dest=False)

    points = [Point(0, 0), Point(10, 0), Point(0, 20)]
    assert _map_points(t_dest, points) == _map_points(t_src, points)

### align Tests ###
@pytest.mark.parametrize("alignment, expected", [
    (Qt.AlignmentFlag.AlignCenter, (40, 25)),
    (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, (0, 25)),
    (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, (80, 25)),
    (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, (40, 0)),
    (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, (40, 50)),
    (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, (80, 50)),
])
def test_align_positions(alignment, expected):
    assert align(20, 10, 100, 60, alignment) == expected

@pytest.mark.parametrize("w, h, expected", [
    (120, 10, (-1, 25)),
    (20, 80, (40, -1)),
    (120, 80, (-1, -1)),
])
def test_align_oversized_axes(w, h, expected):
    assert align(w, h, 100, 60, Qt.AlignmentFlag.AlignCenter) == expected

### alignrect Tests ###
@pytest.mark.parametrize("alignment, expected", [
    (Qt.AlignmentFlag.AlignCenter, (-4, 1)),
    (Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, (10, 1)),
    (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, (-19, 1)),
    (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, (-4, 20)),
    (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, (-4, -19)),
    (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, (-19, -19)),
])
def test_alignrect_positions(alignment, expected, offset_rect, offset_point):
    result = alignrect(offset_rect, offset_point, alignment)

    assert result is None
    assert (offset_rect.x(), offset_rect.y()) == expected
    assert offset_rect.width() == 30
    assert offset_rect.height() == 40

### clamp Tests ###
@pytest.mark.parametrize("value, min_value, max_value, expected", [
    (5, 0, 10, 5),
    (-5, 0, 10, 0),
    (15, 0, 10, 10),
])
def test_clamp(value, min_value, max_value, expected):
    assert clamp(value, min_value, max_value) == expected

### clamp_int32 Tests ###
@pytest.mark.parametrize("value, expected", [
    (0, 0),
    (2**31 - 1, 2**31 - 1),
    (-2**31, -2**31),
    (2**31, 2**31 - 1),
    (-2**31 - 1, -2**31),
])
def test_clamp_int32(value, expected):
    assert clamp_int32(value) == expected

### signalsBlocked Tests ###
class _Emitter(QObject):
    ping = Signal()

    def __init__(self):
        super().__init__()
        self.count = 0
        self.ping.connect(self._on_ping)

    def _on_ping(self):
        self.count += 1

def test_signals_blocked_and_restored():
    obj = _Emitter()
    assert obj.signalsBlocked() is False

    obj.ping.emit()
    assert obj.count == 1

    with signalsBlocked(obj):
        assert obj.signalsBlocked() is True
        obj.ping.emit()
        assert obj.count == 1  # No change

    assert obj.signalsBlocked() is False
    obj.ping.emit()
    assert obj.count == 2

def test_signals_blocked_exception_safety():
    obj = _Emitter()
    assert obj.signalsBlocked() is False

    with pytest.raises(RuntimeError, match="boom"):
        with signalsBlocked(obj):
            assert obj.signalsBlocked() is True
            raise RuntimeError("boom")

    assert obj.signalsBlocked() is False

def test_signals_blocked_multiple():
    a = _Emitter()
    b = _Emitter()

    b.blockSignals(True)
    assert a.signalsBlocked() is False
    assert b.signalsBlocked() is True

    with signalsBlocked(a, b):
        assert a.signalsBlocked() is True
        assert b.signalsBlocked() is True

    assert a.signalsBlocked() is False
    assert b.signalsBlocked() is True  # Still blocked

    b.blockSignals(False)

def test_signals_blocked_no_args():
    with signalsBlocked():
        pass  # Should be a no-op and not raise any exceptions


### autoCropRect Tests ###
def _make_image(width, height, bg=QColor("white")):
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(bg)
    return image

def _paint_rect(image, rect, color=QColor("black")):
    pixel = color.rgba()
    for y in range(rect.y(), rect.y() + rect.height()):
        for x in range(rect.x(), rect.x() + rect.width()):
            image.setPixel(x, y, pixel)

def test_autocroprect_uniform_image_null_rect(qapp):
    image = _make_image(10, 10)
    result = autoCropRect(image)

    assert result == QRect()
    assert result.isNull()

def test_autocroprect_trim_symmetric_border(qapp):
    image = _make_image(10, 10)
    _paint_rect(image, QRect(2, 2, 6, 6))

    assert autoCropRect(image) == QRect(2, 2, 6, 6)

def test_autocroprect_trim_asymmetric_border(qapp):
    image = _make_image(10, 10)
    _paint_rect(image, QRect(1, 3, 9, 4))

    assert autoCropRect(image) == QRect(1, 3, 9, 4)

def test_autocroprect_corner_include_corner_artifact(qapp):
    image = _make_image(8, 8)
    _paint_rect(image, QRect(2, 2, 4, 4))
    _paint_rect(image, QRect(0, 0, 1, 1))

    assert autoCropRect(image) == QRect(0, 0, 6, 6)


### tempdir Tests ###
def test_tempdir_creates_and_cleans_up(qapp):
    p = Path(tempdir())

    assert p.exists()
    assert p.is_dir()

def test_tempdir_returns_unique(qapp):
    first = Path(tempdir())
    second = Path(tempdir())

    assert first != second
    assert first.exists() and first.is_dir()
    assert second.exists() and second.is_dir()

def test_tempdir_shared_parent(qapp):
    first = Path(tempdir())
    second = Path(tempdir())

    assert first.parent == second.parent
    assert first.parent.exists()
    assert first.parent.is_dir()
