import pytest

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest

from qpageview import FixedScale
from qpageview.constants import FitBoth
from qpageview.imageview import ImageView


@pytest.fixture(scope="function")
def imageview(qtbot):
    v = ImageView()
    v.resize(320, 240)
    v.show()
    qtbot.addWidget(v)
    return v

@pytest.fixture(scope="function")
def image():
    img = QImage(120, 80, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.green)
    return img


def test_image_view_defaults(imageview):
    assert imageview.viewMode() == FitBoth
    margins = imageview.pageLayout().margins()
    assert margins.left() == 0
    assert margins.top() == 0
    assert margins.right() == 0
    assert margins.bottom() == 0

def test_image_loads_single_page_doc(imageview, image):
    imageview.setImage(image)

    doc = imageview.document()
    assert doc is not None
    assert doc.count() == 1

def test_image_view_zoom_toggles(imageview):
    assert imageview.viewMode() == FitBoth

    imageview.toggleZooming()
    assert imageview.viewMode() == FixedScale

    imageview.toggleZooming()
    assert imageview.viewMode() == FitBoth

def test_lmb_up_toggles_zoom(imageview):
    assert imageview.viewMode() == FitBoth

    QTest.mouseRelease(imageview.viewport(), Qt.MouseButton.LeftButton)
    assert imageview.viewMode() == FixedScale

def test_rmb_up_does_not_toggle_zoom(imageview):
    assert imageview.viewMode() == FitBoth

    QTest.mouseRelease(imageview.viewport(), Qt.MouseButton.RightButton)
    assert imageview.viewMode() == FitBoth

def test_page_layout_caps_zoom(imageview, image):
    imageview.setImage(image)
    imageview.fitNaturalSizeEnabled = True
    imageview.setViewMode(FitBoth)

    imageview.fitPageLayout()

    layout = imageview.pageLayout()
    factor = layout[0].dpi / imageview.physicalDpiX()
    assert layout.zoomFactor <= factor

def test_page_layout_natural_size_disabled_allows_fit(imageview, image):
    imageview.setImage(image)
    imageview.fitNaturalSizeEnabled = False
    imageview.setViewMode(FitBoth)

    imageview.fitPageLayout()

    assert imageview.pageLayout().zoomFactor > 0
