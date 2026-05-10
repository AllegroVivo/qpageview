import pytest
from PySide6.QtCore import QRect, QBuffer, QSize
from PySide6.QtGui import QColor, QImage, QPainter

from qpageview.image import ImageContainer, ImageLoader, ImagePage, ImageDocument


@pytest.fixture(scope="function")
def image():
    img = QImage(20, 40, QImage.Format.Format_ARGB32)
    img.fill(QColor("green"))
    return img

### ImageContainer Tests ###
def test_image_container_returns_original_image(image):
    container = ImageContainer(image)
    assert container.image() == image

def test_image_container_returns_clipped_image(image):
    image.setPixelColor(5, 5, QColor("red"))
    container = ImageContainer(image)

    clipped = container.image(QRect(4, 4, 4, 4))

    assert clipped.size() == QSize(4, 4)
    assert clipped.pixelColor(1, 1) == QColor("red")

def test_image_loader_size_null_for_invalid_source():
    loader = ImageLoader("nonexistent_file.jpg")
    assert loader.image().isNull()

def test_image_loader_qiodevice():
    image = QImage(8, 6, QImage.Format.Format_ARGB32)
    image.fill(QColor("green"))
    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.ReadWrite)
    image.save(buf, "PNG")  # type: ignore
    buf.seek(0)

    loader = ImageLoader(buf)
    loaded = loader.image()

    assert not loaded.isNull()
    assert loaded.size() == image.size()

### ImagePage Tests ###
def test_image_page_has_expected_size(image):
    page = ImagePage.fromImage(image)

    assert page.pageWidth == 20
    assert page.pageHeight == 40
    assert page.defaultSize().toSize() == image.size()

def test_image_page_load_yields_page(tmp_path, image):
    img_path = tmp_path / "test_image.png"
    image.save(str(img_path))

    pages = list(ImagePage.load(str(img_path)))

    assert len(pages) == 1
    assert pages[0].pageWidth == 20
    assert pages[0].pageHeight == 40
    assert pages[0].defaultSize().toSize() == image.size()

def test_image_page_invalid_file(tmp_path, image):
    img_path = tmp_path / "invalid_image.png"
    img_path.write_bytes(b"not an image")

    pages = list(ImagePage.load(str(img_path)))

    assert len(pages) == 1
    rendered = pages[0].image()
    assert rendered.isNull()

def test_image_page_return_full_image_with_null_rect(image):
    page = ImagePage.fromImage(image)
    page.width = 20
    page.height = 40

    result = page.image(QRect(0, 0, 10, 5))

    assert not result.isNull()
    assert result.size() == QSize(10, 5)

def test_image_page_print_uses_target_painter():
    source = QImage(10, 10, QImage.Format.Format_ARGB32)
    source.fill(QColor("green"))
    page = ImagePage.fromImage(source)

    target = QImage(10, 10, QImage.Format.Format_ARGB32)
    target.fill(QColor("white"))

    painter = QPainter(target)
    page.print(painter)
    painter.end()

    assert target.pixelColor(5, 5) == QColor("green")


### ImageDocument Tests ###
def test_image_document_pages(image):
    invalid = QImage()

    doc = ImageDocument([image, invalid])
    pages = list(doc.createPages())

    assert len(pages) == 1
    assert isinstance(pages[0], ImagePage)

def test_image_document_from_file_paths(tmp_path, image):
    img_path = tmp_path / "test_image.png"
    assert image.save(str(img_path))

    doc = ImageDocument([str(img_path)])
    pages = list(doc.createPages())

    assert len(pages) == 1
    assert pages[0].pageWidth == 20
    assert pages[0].pageHeight == 40
    assert pages[0].defaultSize().toSize() == image.size()

def test_image_document_from_mixed_sources(tmp_path, image):
    img_path = tmp_path / "test_image.png"
    assert image.save(str(img_path))

    invalid = QImage()

    doc = ImageDocument([str(img_path), invalid, image])
    pages = list(doc.createPages())

    assert len(pages) == 2
    assert pages[0].defaultSize().toSize() == image.size()
    assert pages[1].defaultSize().toSize() == image.size()
