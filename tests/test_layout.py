import pytest
from PySide6.QtCore import QPoint, QRect, QSize

from qpageview.constants import Vertical, Horizontal, FitWidth, FitHeight, Rotate_90, Rotate_270
from qpageview.layout import PageLayout, LayoutEngine, RowLayoutEngine, RasterLayoutEngine


class _MockPage:
    def __init__(self, w=100, h=200, dpi=100.0, rotation=0, scale_x=1.0, scale_y=1.0):
        self.x = 0
        self.y = 0
        self.width = w
        self.height = h
        self.pageWidth = w
        self.pageHeight = h
        self.dpi = dpi
        self.rotation = rotation
        self.computedRotation = rotation
        self.scaleX = scale_x
        self.scaleY = scale_y
        self.update_size_calls = []
        self.zoom_for_width_calls = []
        self.zoom_for_height_calls = []

    def pos(self):
        return QPoint(self.x, self.y)

    def geometry(self):
        return QRect(self.x, self.y, self.width, self.height)

    def updateSize(self, dpi_x, dpi_y, zoom_factor):
        self.update_size_calls.append((dpi_x, dpi_y, zoom_factor))
        self.width = int(round(self.pageWidth * zoom_factor))
        self.height = int(round(self.pageHeight * zoom_factor))

    def zoomForWidth(self, width, rotation, dpi_x):
        self.zoom_for_width_calls.append((width, rotation, dpi_x))
        base = self.pageWidth if (self.rotation + rotation) & Rotate_90 else self.pageHeight
        return width / base if base else 1.0

    def zoomForHeight(self, height, rotation, dpi_y):
        self.zoom_for_height_calls.append((height, rotation, dpi_y))
        base = self.pageHeight if (self.rotation + rotation) & Rotate_90 else self.pageWidth
        return height / base if base else 1.0


@pytest.fixture(scope="function")
def layout():
    l = PageLayout()
    l.engine = LayoutEngine()
    l.clear()
    return l

### PageLayout Tests ###
def test_page_layout_empty(layout):
    assert layout.count() == 0

    assert layout.empty() is True
    assert bool(layout) is True

    assert layout.widestPage() is None
    assert layout.highestPage() is None

def test_page_layout_add_page(layout):
    layout.extend([_MockPage(), _MockPage()])

    assert layout.count() == 2
    assert layout.empty() is False

def test_page_layout_margins_set_and_read(layout):
    m = layout.margins()
    pm = layout.pageMargins()

    assert m.left() >= 0
    assert pm.left() >= 0

def test_page_layout_dimensions_respect_rotation(layout):
    p = _MockPage()
    layout.rotation = Rotate_90

    assert layout.defaultWidth(p) == pytest.approx(2.0)  # type: ignore
    assert layout.defaultHeight(p) == pytest.approx(1.0)  # type: ignore

def test_page_layout_widest_and_highest_page(layout):
    p1 = _MockPage()
    p2 = _MockPage(w=150, h=150)
    layout.extend([p1, p2])

    assert layout.widestPage() is p2
    assert layout.highestPage() is p1

def test_page_layout_update(layout):
    p1 = _MockPage(rotation=Rotate_90)
    p2 = _MockPage(rotation=Rotate_270)
    layout.extend([p1, p2])
    layout.rotation = Rotate_90
    layout.zoomFactor = 1.5
    layout.dpiX = 90.0
    layout.dpiY = 110.0

    changed = layout.update()

    assert changed is True
    assert p1.update_size_calls[-1] == (90.0, 110.0, 1.5)
    assert p2.update_size_calls[-1] == (90.0, 110.0, 1.5)
    assert p1.computedRotation == 2
    assert p2.computedRotation == 0

def test_page_layout_update_no_change(layout):
    layout.append(_MockPage())

    layout.update()  # First update to set initial state
    changed = layout.update()  # Second update with no changes

    assert changed is False

def test_page_layout_at_and_nearest(layout):
    p1 = _MockPage()
    p2 = _MockPage()
    layout.extend([p1, p2])
    layout.orientation = Horizontal
    layout.spacing = 0
    layout.setMargins(layout.margins().__class__(0, 0, 0, 0))
    layout.setPageMargins(layout.pageMargins().__class__(0, 0, 0, 0))
    layout.update()

    assert layout.pageAt(QPoint(10, 10)) is p1
    assert layout.pageAt(QPoint(110, 10)) is p2
    assert layout.nearestPageAt(QPoint(200, 10)) in {p1, p2}

def test_page_layout_pages_at(layout):
    p1 = _MockPage()
    p2 = _MockPage()
    layout.extend([p1, p2])
    layout.orientation = Horizontal
    layout.spacing = 0
    layout.setMargins(layout.margins().__class__(0, 0, 0, 0))
    layout.setPageMargins(layout.pageMargins().__class__(0, 0, 0, 0))
    layout.update()

    pages = list(layout.pagesAt(QRect(80, 0, 30, 30)))

    assert p1 in pages
    assert p2 in pages

def test_page_layout_pos2offset_round_trip(layout):
    p = _MockPage()
    layout.append(p)
    layout.setMargins(layout.margins().__class__(0, 0, 0, 0))
    layout.setPageMargins(layout.pageMargins().__class__(0, 0, 0, 0))
    layout.update()

    point = QPoint(25, 50)
    offset = layout.pos2offset(point)
    pos = layout.offset2pos(offset)

    assert pos == point

def test_page_layout_pos2offset_no_pages(layout):
    layout.width = 200
    layout.height = 100

    idx, ox, oy = layout.pos2offset(QPoint(100, 50))

    assert idx == -1
    assert ox == pytest.approx(0.5)
    assert oy == pytest.approx(0.5)

def test_page_layout_current_page_set_slice(layout):
    layout.extend([_MockPage(), _MockPage(), _MockPage()])
    layout.continuousMode = True

    s = layout.currentPageSetSlice()

    assert s.start == 0
    assert s.stop == 3

### Various LayoutEngine Tests ###
def test_row_layout_engine_non_continuous_mode_clamping(layout):
    layout.engine = RowLayoutEngine()
    layout.engine.pagesPerRow = 2
    layout.engine.pagesPerFirstRow = 1
    layout.extend([_MockPage(), _MockPage(), _MockPage()])
    layout.continuousMode = False
    layout.currentPageSet = 99

    s = layout.currentPageSetSlice()

    assert s.start >= 0
    assert s.stop <= 3
    assert layout.currentPageSet == layout.pageSetCount() - 1

def test_row_layout_engine_page_set_indices(layout):
    layout.engine = RowLayoutEngine()
    layout.engine.pagesPerRow = 2
    layout.engine.pagesPerFirstRow = 1
    layout.extend([_MockPage(), _MockPage(), _MockPage(), _MockPage()])

    assert layout.pageSetCount() == 3
    assert layout.pageSet(0) == 0
    assert layout.pageSet(1) == 1
    assert layout.pageSet(2) == 1
    assert layout.pageSet(3) == 2

def test_layout_engine_grid_orientation(layout):
    layout.extend([_MockPage(), _MockPage(), _MockPage()])

    layout.orientation = Vertical
    assert layout.engine.grid(layout) == (1, 3, 0)

    layout.orientation = Horizontal
    assert layout.engine.grid(layout) == (3, 1, 0)

def test_layout_engine_zoom_factor(layout):
    p = _MockPage()
    layout.append(p)
    layout.setMargins(layout.margins().__class__(0, 0, 0, 0))
    layout.setPageMargins(layout.pageMargins().__class__(0, 0, 0, 0))
    layout.engine = LayoutEngine()

    layout.fit(QSize(20, 400), FitWidth | FitHeight)

    assert layout.zoomFactor == pytest.approx(0.1)

def test_row_layout_engine_page_sets():
    engine = RowLayoutEngine()
    engine.pagesPerRow = 3
    engine.pagesPerFirstRow = 1

    assert engine.pageSets(0) == []
    assert engine.pageSets(1) == [(1, 1)]
    assert engine.pageSets(2) == [(2, 1)]
    assert engine.pageSets(5) == [(1, 1), (1, 3), (1, 1)]

def test_row_layout_engine_includes_prepend(layout):
    layout.engine = RowLayoutEngine()
    layout.engine.pagesPerRow = 3
    layout.engine.pagesPerFirstRow = 1
    layout.extend([_MockPage(), _MockPage(), _MockPage(), _MockPage()])

    ncols, nrows, prepend = layout.engine.grid(layout)

    assert ncols == 3
    assert nrows == 2
    assert prepend == 2

def test_raster_layout_engine_multiple_columns(layout):
    layout.engine = RasterLayoutEngine()
    layout.extend([_MockPage(), _MockPage(), _MockPage(), _MockPage()])
    layout.spacing = 0
    layout.setMargins(layout.margins().__class__(0, 0, 0, 0))
    layout.setPageMargins(layout.pageMargins().__class__(0, 0, 0, 0))
    layout.update()

    layout.engine.fit(layout, QSize(260, 200), FitWidth)
    ncols, nrows, prepend = layout.engine.grid(layout)

    assert prepend == 0
    assert ncols >= 2
    assert nrows >= 1

def tets_raster_layout_engine_multiple_rows(layout):
    layout.engine = RasterLayoutEngine()
    layout.extend([_MockPage(), _MockPage(), _MockPage(), _MockPage()])
    layout.spacing = 0
    layout.setMargins(layout.margins().__class__(0, 0, 0, 0))
    layout.setPageMargins(layout.pageMargins().__class__(0, 0, 0, 0))
    layout.update()

    layout.engine.fit(layout, QSize(200, 260), FitHeight)
    ncols, nrows, prepend = layout.engine.grid(layout)

    assert prepend == 0
    assert ncols >= 1
    assert nrows >= 2
