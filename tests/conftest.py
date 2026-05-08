import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QTransform

from qpageview.util import Point

@pytest.fixture(scope="function")
def identity_point():
    """Fixture that provides a point with coordinates (0, 0)."""
    return Point(0, 0)

@pytest.fixture(scope="function")
def offset_point():
    """Fixture that provides a point with coordinates (10, 20)."""
    return Point(10, 20)

@pytest.fixture(scope="function")
def identity_transform():
    """Fixture that provides an identity QTransform."""
    return QTransform()

@pytest.fixture(scope="function")
def identity_rect():
    """Fixture that provides a QRect with coordinates (0, 0) and size (0, 0)."""
    return QRect(0, 0, 0, 0)

@pytest.fixture(scope="function")
def offset_rect():
    """Fixture that provides a QRect with coordinates (10, 20) and size (30, 40)."""
    return QRect(10, 20, 30, 40)













