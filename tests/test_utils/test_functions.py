import pytest
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QTransform

from qpageview.util import (
    rotate, Point, align, alignrect, clamp, clamp_int32
)
from qpageview.constants import (
    Rotate_0, Rotate_90, Rotate_180, Rotate_270
)

def _map_points(t, points):
    return [t.map(p) for p in points]

### rotate Tests ###
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









