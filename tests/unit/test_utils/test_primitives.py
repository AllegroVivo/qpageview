import pytest
from PySide6.QtCore import QPoint, QSize, QRect, QRectF, QPointF
from PySide6.QtGui import QTransform

from qpageview.util import Rectangular, MapToPage, Point, clamp_int32

### Rectangular Tests ###
@pytest.fixture(scope="function")
def rectangular():
    return Rectangular()

def _assert_rect_equals(rect, x, y, w, h):
    assert rect.x == x
    assert rect.y == y
    assert rect.width == w
    assert rect.height == h

    assert rect.pos() == QPoint(x, y)
    assert rect.size() == QSize(w, h)
    assert rect.geometry() == QRect(x, y, w, h)
    assert rect.rect() == QRect(0, 0, w, h)

def _assert_point_equals(point, x, y):
    assert point.x() == x
    assert point.y() == y

def test_rectangular_base_values(rectangular):
    _assert_rect_equals(rectangular, 0, 0, 0, 0)

@pytest.mark.parametrize("x, y, width, height", [
    (10, 20, 30, 40),
    (-5, -10, 15, 25),
    (150, 250, 100, 200),
])
def test_rectangular_setters(rectangular, x, y, width, height):
    rectangular.setPos(QPoint(x, y))
    _assert_rect_equals(rectangular, x, y, 0, 0)
    rectangular.setSize(QSize(width, height))
    _assert_rect_equals(rectangular, x, y, width, height)
    x += 5
    y += 5
    width += 10
    height += 10
    rectangular.setGeometry(QRect(x, y, width, height))
    _assert_rect_equals(rectangular, x, y, width, height)

### MapToPage Tests ###
@pytest.fixture(scope="function")
def identity_mapper():
    return MapToPage(QTransform())

@pytest.fixture(scope="function")
def scale_mapper():
    transform = QTransform()
    transform.scale(2.0, 2.0)
    return MapToPage(transform)

@pytest.fixture(scope="function")
def translate_mapper():
    transform = QTransform()
    transform.translate(10.0, 20.0)
    return MapToPage(transform)

def test_identity_mapper(identity_mapper):
    rect = QRect(10, 20, 30, 40)
    assert identity_mapper.rect(rect) == rect
    point = QPoint(10, 20)
    assert identity_mapper.point(point) == point

def test_scale_mapper(scale_mapper):
    rect = QRect(10, 20, 30, 40)
    expected_rect = QRect(20, 40, 60, 80)
    assert scale_mapper.rect(rect) == expected_rect
    point = QPoint(10, 20)
    expected_point = QPoint(20, 40)
    assert scale_mapper.point(point) == expected_point

def test_translate_mapper(translate_mapper):
    rect = QRect(10, 20, 30, 40)
    expected_rect = QRect(20, 40, 30, 40)
    assert translate_mapper.rect(rect) == expected_rect
    point = QPoint(10, 20)
    expected_point = QPoint(20, 40)
    assert translate_mapper.point(point) == expected_point

def test_mapper_float_to_int_truncation(identity_mapper):
    rect = QRectF(10.7, 20.3, 30.9, 40.1)
    expected_rect = QRect(11, 20, 31, 40)
    assert identity_mapper.rect(rect) == expected_rect
    point = QPointF(10.7, 20.3)
    expected_point = QPoint(11, 20)
    assert identity_mapper.point(point) == expected_point

### Point Tests ###
INT_MIN = -2**31
INT_MAX = 2**31 - 1

@pytest.fixture(scope="function")
def point():
    return Point(0, 0)

def test_point_base_values(point):
    _assert_point_equals(point, 0, 0)

@pytest.mark.parametrize("x, y", [
    (10, 20),
    (-5, -10),
    (INT_MIN, INT_MAX),
    (INT_MAX, INT_MIN),
    (INT_MIN - 1, INT_MAX + 1),  # Test clamping on overflow
])
def test_point_setters(point, x: int, y: int):
    point.setX(x)
    point.setY(y)
    expected_x = clamp_int32(x)
    expected_y = clamp_int32(y)
    _assert_point_equals(point, expected_x, expected_y)



















