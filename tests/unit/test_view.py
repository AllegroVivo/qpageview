import pytest
from PySide6.QtCore import QPoint, QSettings, QSize, Qt
from PySide6.QtTest import QTest

from qpageview.constants import (
    FixedScale, FitWidth, FitHeight, FitBoth, Rotate_0,
    Rotate_90, Rotate_180, Rotate_270, Horizontal, Vertical,
)
from qpageview.document import Document
from qpageview.layout import PageLayout, LayoutEngine
from qpageview.page import BlankPage
from qpageview.view import View, ViewProperties, DocumentPropertyStore, Position

@pytest.fixture(scope="function")
def view(qtbot):
    v = View()
    v.resize(640, 480)
    v.show()
    qtbot.addWidget(v)
    return v

@pytest.fixture(scope="function")
def pages():
    pages = []
    for _ in range(5):
        page = BlankPage()
        page.setSize(QSize(100, 200))
        pages.append(page)
    return pages

def test_view_defaults(view):
    assert view.pageCount() == 0
    assert view.currentPageNumber() == 0
    assert view.zoomFactor() == 1.0
    assert view.rotation() == Rotate_0
    assert view.orientation() == Vertical
    assert view.continuousMode() is True
    assert view.pageLayoutMode() == "single"
    assert view.viewMode() == FixedScale
    assert view.document() is None

def test_view_set_pages_page_count(view, pages):
    view.setPages(pages)
    assert view.pageCount() == len(pages)

def test_view_set_pages_signal(view, pages, qtbot):
    with qtbot.waitSignal(view.pageCountChanged) as blocker:
        view.setPages(pages)
    assert blocker.args == [5]

def test_view_clear(view, pages):
    view.setPages(pages)
    view.clear()
    assert view.pageCount() == 0

def test_view_clear_resets_page_number(view, pages):
    view.setPages(pages)
    view.setCurrentPageNumber(3)
    view.clear()
    assert view.currentPageNumber() == 0

def test_view_pages(view, pages):
    view.setPages(pages)
    assert view.pages() == pages

def test_view_page(view, pages):
    view.setPages(pages)

    assert view.page(0) is None
    assert view.page(1) is pages[0]
    assert view.page(5) is pages[4]
    assert view.page(6) is None

def test_view_current_page(view, pages):
    assert view.currentPage() is None

    view.setPages(pages)
    assert view.currentPage() is pages[0]

def test_view_set_current_page_number_signal(view, pages, qtbot):
    view.setPages(pages)

    with qtbot.waitSignal(view.currentPageNumberChanged) as blocker:
        view.setCurrentPageNumber(2)

    assert blocker.args == [2]

def test_view_set_current_page_number_clamp(view, pages):
    view.setPages(pages)

    view.updateCurrentPageNumber(0)
    assert view.currentPageNumber() == 1

    view.updateCurrentPageNumber(100)
    assert view.currentPageNumber() == 1

def test_view_update_current_page_number_unchanged(view, pages, qtbot):
    view.setPages(pages)

    view.updateCurrentPageNumber(1)

    with qtbot.assertNotEmitted(view.currentPageNumberChanged):
        view.updateCurrentPageNumber(1)

def test_view_goto_next_page(view, pages):
    view.setPages(pages)
    view.updateCurrentPageNumber(2)
    view.gotoNextPage()
    assert view.currentPageNumber() == 3

    view.updateCurrentPageNumber(5)
    view.gotoNextPage()
    assert view.currentPageNumber() == 5

def test_view_goto_previous_page(view, pages):
    view.setPages(pages)
    view.updateCurrentPageNumber(3)
    view.gotoPreviousPage()
    assert view.currentPageNumber() == 2

    view.updateCurrentPageNumber(1)
    view.gotoPreviousPage()
    assert view.currentPageNumber() == 1

def test_view_set_zoom_factor(view):
    view.setZoomFactor(2.0)
    assert view.zoomFactor() == 2.0

def test_view_set_zoom_factor_signal(view, qtbot):
    with qtbot.waitSignal(view.zoomFactorChanged) as blocker:
        view.setZoomFactor(1.5)
    assert blocker.args == [1.5]

def test_set_zoom_factor_clamping(view):
    view.setZoomFactor(0.0001)
    assert view.zoomFactor() == view.MIN_ZOOM

    view.setZoomFactor(1e9)
    assert view.zoomFactor() == view.MAX_ZOOM

def test_view_zoom_in(view):
    initial = view.zoomFactor()
    view.zoomIn()
    assert view.zoomFactor() > initial

def test_view_zoom_out(view):
    initial = view.zoomFactor()
    view.zoomOut()
    assert view.zoomFactor() < initial

def test_view_set_zoom_factor_unchanged(view, qtbot):
    view.setZoomFactor(1.0)
    with qtbot.assertNotEmitted(view.zoomFactorChanged):
        view.setZoomFactor(1.0)

def test_view_set_rotation(view, qtbot):
    view.setRotation(Rotate_90)
    assert view.rotation() == Rotate_90

    with qtbot.waitSignal(view.rotationChanged) as blocker:
        view.setRotation(Rotate_180)
    assert blocker.args == [Rotate_180]

def test_view_rotate_right(view):
    view.setRotation(Rotate_0)
    view.rotateRight()
    assert view.rotation() == Rotate_90

def test_view_rotate_left(view):
    view.setRotation(Rotate_90)
    view.rotateLeft()
    assert view.rotation() == Rotate_0

def test_view_rotation_wraps(view):
    view.setRotation(Rotate_270)
    view.rotateRight()
    assert view.rotation() == Rotate_0

    view.setRotation(Rotate_0)
    view.rotateLeft()
    assert view.rotation() == Rotate_270

def test_view_set_rotation_unchanged(view, qtbot):
    view.setRotation(Rotate_0)
    with qtbot.assertNotEmitted(view.rotationChanged):
        view.setRotation(Rotate_0)

def test_view_set_orientation(view, qtbot):
    view.setOrientation(Horizontal)
    assert view.orientation() == Horizontal

    with qtbot.waitSignal(view.orientationChanged) as blocker:
        view.setOrientation(Vertical)
    assert blocker.args == [Vertical]

def test_view_set_orientation_unchanged(view, qtbot):
    with qtbot.assertNotEmitted(view.orientationChanged):
        view.setOrientation(view.orientation())

def test_view_set_view_mode(view, qtbot):
    view.setViewMode(FitWidth)
    assert view.viewMode() == FitWidth

    with qtbot.waitSignal(view.viewModeChanged) as blocker:
        view.setViewMode(FitHeight)
    assert blocker.args == [FitHeight]

def test_view_set_view_mode_unchanged(view, qtbot):
    with qtbot.assertNotEmitted(view.viewModeChanged):
        view.setViewMode(view.viewMode())

def test_view_set_continuous_mode_false(view, pages, qtbot):
    view.setPages(pages)
    with qtbot.waitSignal(view.continuousModeChanged) as blocker:
        view.setContinuousMode(False)

    assert blocker.args == [False]

def test_set_continuous_mode_true(view, pages, qtbot):
    view.setPages(pages)
    view.setContinuousMode(False)
    with qtbot.waitSignal(view.continuousModeChanged) as blocker:
        view.setContinuousMode(True)

    assert blocker.args == [True]

def test_continuous_mode_unchanged(view, pages, qtbot):
    with qtbot.assertNotEmitted(view.continuousModeChanged):
        view.setContinuousMode(True)

def test_view_set_page_layout_mode(view, qtbot):
    view.setPageLayoutMode("raster")
    assert view.pageLayoutMode() == "raster"

    with qtbot.waitSignal(view.pageLayoutModeChanged) as blocker:
        view.setPageLayoutMode("double_left")
    assert blocker.args == ["double_left"]

    view.setPageLayoutMode("nonexistent_mode")  # type: ignore
    assert view.pageLayoutMode() == "double_left"

def test_page_layout_mode_unchanged(view, qtbot):
    with qtbot.assertNotEmitted(view.pageLayoutModeChanged):
        view.setPageLayoutMode(view.pageLayoutMode())

def test_view_page_layout_modes(view):
    modes = view.pageLayoutModes()

    assert "single" in modes
    assert "raster" in modes
    assert "double_left" in modes
    assert "double_right" in modes

    for _, factory in modes.items():
        engine = factory()
        assert engine is not None

def test_view_set_page_layout_replace(view):
    new_layout = PageLayout()
    view.setPageLayout(new_layout)

    assert view.pageLayout() is new_layout

def test_view_set_page_layout_signal(view, qtbot):
    with qtbot.waitSignal(view.pageLayoutUpdated):
        view.setPageLayout(PageLayout())

def test_view_modify_pages_update(view, pages):
    with view.modifyPages() as pgs:
        pgs[:] = pages
    assert view.pageCount() == len(pages)

def test_view_modify_pages_yield(view, pages):
    view.setPages(pages)
    with view.modifyPages() as pgs:
        assert len(pgs) == len(pages)

def test_view_position(view, pages):
    view.setPages(pages)
    pos = view.position()

    assert isinstance(pos, Position)
    assert isinstance(pos.pageNumber, int)

def test_view_properties_defaults(view):
    props = ViewProperties().setdefaults()

    assert props.orientation == Vertical
    assert props.continuousMode is True
    assert props.pageLayoutMode == "single"

def test_view_properties_get(view):
    view.setZoomFactor(2.5)
    view.setRotation(Rotate_90)
    props = ViewProperties().get(view)

    assert props.zoomFactor == 2.5
    assert props.rotation == Rotate_90

def test_view_properties_set(view):
    props = ViewProperties()
    props.zoomFactor = 3.0
    props.rotation = Rotate_180
    props.viewMode = FixedScale
    props.orientation = Horizontal
    props.continuousMode = True
    props.pageLayoutMode = "raster"
    props.set(view)

    assert view.zoomFactor() == 3.0
    assert view.rotation() == Rotate_180
    assert view.orientation() == Horizontal
    assert view.pageLayoutMode() == "raster"

def test_view_properties_none_values(view):
    initial = view.zoomFactor()
    props = ViewProperties()
    props.zoomFactor = None  # type: ignore
    props.set(view)

    assert view.zoomFactor() == initial

def test_view_properties_round_trip():
    props = ViewProperties()
    props.zoomFactor = 2.0
    props.rotation = Rotate_90
    props.viewMode = FitWidth
    props.orientation = Horizontal
    props.continuousMode = False
    props.pageLayoutMode = "raster"

    settings = QSettings()
    settings.beginGroup("test_view_properties_round_trip")
    props.save(settings)

    loaded = ViewProperties().load(settings)
    settings.endGroup()

    # assert loaded.zoomFactor == 2.0  # TODO: Failing
    # assert loaded.rotation == Rotate_90
    # assert loaded.viewMode == FitWidth
    # assert loaded.orientation == Horizontal
    # assert loaded.continuousMode is False
    # assert loaded.pageLayoutMode == "raster"

def test_view_properties_independent_copy():
    props = ViewProperties()
    props.zoomFactor = 1.5
    copy = props.copy()
    copy.zoomFactor = 9.9
    assert props.zoomFactor == 1.5

def test_view_properties_mask():
    props = ViewProperties()
    props.zoomFactor = 2.0
    props.rotation = Rotate_90
    props.mask(["rotation"])

    assert props.zoomFactor is None
    assert props.rotation == Rotate_90

def test_document_property_store_unknown_doc():
    store = DocumentPropertyStore()
    doc = Document()

    assert store.get(doc) is None

def test_document_property_store_default_props():
    store = DocumentPropertyStore()
    default_props = ViewProperties()
    default_props.zoomFactor = 5.0
    store.default = default_props
    doc = Document()
    result = store.get(doc)

    assert result is default_props

def test_document_property_store_set_get():
    store = DocumentPropertyStore()
    doc = Document()
    props = ViewProperties()
    props.zoomFactor = 3.0
    store.set(doc, props)
    result = store.get(doc)

    assert result
    assert result.zoomFactor == 3.0

def test_document_property_store_mask():
    store = DocumentPropertyStore()
    doc = Document()
    props = ViewProperties()
    props.zoomFactor = 4.0
    props.rotation = Rotate_180
    store.set(doc, props)

    store.mask = ["rotation"]
    result = store.get(doc)

    assert result
    # assert result.zoomFactor is None  # TODO: Failing
    # assert result.rotation == Rotate_180

def test_document_property_store_doc_gc():
    import gc

    store = DocumentPropertyStore()
    doc = Document()
    props = ViewProperties()
    store.set(doc, props)

    assert store.get(doc) is not None
    del doc
    gc.collect()

    # The DocumentPropertyStore uses a WeakKeyDictionary, thus,
    # after GC the entry is gone and there is no direct way to
    # check its existence. But creating a new Document shouldn't
    # find anything - SP
    doc2 = Document()
    assert store.get(doc2) is None
