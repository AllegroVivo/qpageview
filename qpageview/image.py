# -*- coding: utf-8 -*-
#
# This file is part of the qpageview package.
#
# Copyright (c) 2019 - 2019 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
A page that can display an image, loaded using QImage.

ImagePages are instantiated quite fast. The image is only really loaded on first
display.

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Iterator

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QIODevice, QRectF
from PySide6.QtGui import QImage, QImageIOHandler, QImageReader, QTransform, QPainter, QColor

from .document import MultiSourceDocument
from . import locking
from .page import AbstractRenderedPage
from .render import AbstractRenderer

if TYPE_CHECKING:
    from .render import Key, Tile

class ImageContainer:
    """Represents an image, and is shared among copies of the "same" Page."""
    def __init__(self, image: QImage):
        """Init with a QImage."""
        self._image: QImage = image

    def size(self) -> QSize:
        return self._image.size()

    def image(self, clip: Optional[QRect] = None) -> QImage:
        if clip is None:
            return self._image
        return self._image.copy(clip)


class ImageLoader(ImageContainer):
    """Represent an image loaded from a file or IO device."""
    # noinspection PyMissingConstructor
    def __init__(self, source: Union[str, QIODevice], autoTransform: bool = True):
        """Init with a filename or QIODevice.

        If autoTransform is True (the default), EXIF rotation is automatically
        applied when loading the image.

        """
        self._size: Optional[QSize] = None
        self.source: Union[str, QIODevice] = source
        self.autoTransform: bool = autoTransform

    def _reader(self) -> QImageReader:
        """Return a QImageReader for the source."""
        reader = QImageReader(self.source)  # type: ignore - QImageReader has overloads for both str and QIODevice - SP
        reader.setAutoTransform(self.autoTransform)
        return reader

    def size(self) -> QSize:
        """Return the size of the image.

        If the image can't be loaded, a null size is returned. The resulting
        value is cached.

        """
        if self._size is None:
            self._size = QSize()
            reader = self._reader()
            if reader.canRead():
                size = reader.size()
                if size:
                    if self.autoTransform and reader.transformation() & QImageIOHandler.Transformation.TransformationRotate90:
                        size.transpose()
                    self._size = size
        assert self._size is not None  # for type checker - SP
        return QSize(self._size)

    def image(self, clip: Optional[QRect] = None):
        """Load and return the image.

        If clip is given, it should be a QRect describing the area to load.

        """
        with locking.lock(self):
            reader = self._reader()
            if clip:
                if self.autoTransform:
                    size = reader.size()
                    transf = reader.transformation()
                    m = QTransform()
                    m.translate(size.width() / 2, size.height() / 2)
                    if transf & QImageIOHandler.Transformation.TransformationMirror:
                        # horizontal mirror
                        m.scale(-1, 1)
                    if transf & QImageIOHandler.Transformation.TransformationFlip:
                        # vertical mirror
                        m.scale(1, -1)
                    if transf & QImageIOHandler.Transformation.TransformationRotate90:
                        # rotate 90
                        m.rotate(-90)
                        m.translate(size.height() / -2, size.width() / -2)
                    else:
                        m.translate(size.width() / -2, size.height() / -2)
                    clip = m.mapRect(clip)
                reader.setClipRect(clip)
            return reader.read()


class ImagePage(AbstractRenderedPage):
    """A Page that displays an image in any file format supported by Qt."""
    autoTransform: bool = True    # whether to automatically apply exif transformations
    dpi = 96   # TODO: maybe this can be image dependent.

    def __init__(self, container: ImageContainer, renderer: Optional[AbstractRenderer] = None):
        super().__init__(renderer)
        self.setPageSize(container.size())  # type: ignore - ImageContainer.size() returns QSize, but setPageSize expects QSizeF - SP
        self._ic: ImageContainer = container

    @classmethod
    def load(
        cls,
        filename: Union[str, QIODevice],
        renderer: Optional[AbstractRenderer] = None
    ) -> Iterator[ImagePage]:
        """Load the image and yield one ImagePage instance if loading was successful."""
        loader = ImageLoader(filename, cls.autoTransform)
        if loader.size():
            yield cls(loader, renderer)

    @classmethod
    def fromImage(cls, image: QImage, renderer: Optional[AbstractRenderer] = None) -> ImagePage:
        """Instantiate one ImagePage from the supplied QImage.

        As the image is kept in memory, it is not advised to instantiate many
        Page instances this way. Use load() for images on the filesystem.
        The image must be valid, and have a size > 0.

        """
        return cls(ImageContainer(image), renderer)

    def print(
        self,
        painter: QPainter,
        rect: Optional[QRectF] = None,
        paperColor: Optional[QColor] = None
    ) -> None:
        """Paint a page for printing."""
        if rect is None:
            image = self._ic.image()
        else:
            rect = rect.normalized() & self.pageRect()
            # we copy the image, because QSvgGenerator otherwise includes the
            # full image in the resulting SVG file!
            image = self._ic.image(rect.toRect())
        painter.drawImage(QPoint(0, 0), image)

    def image(
        self,
        rect: Optional[QRect] = None,
        dpiX: int = None,
        dpiY: int = None,
        paperColor: Optional[QColor] = None
    ):
        """Return a QImage of the specified rectangle."""
        if rect is None:
            rect = self.rect()
        else:
            rect = rect & self.rect()
        if dpiX is None:
            dpiX = self.dpi
        if dpiY is None:
            dpiY = dpiX

        s = self.defaultSize()
        m = QTransform()
        m.scale(s.width() * dpiX / self.dpi, s.height() * dpiY / self.dpi)
        m.translate(.5, .5)
        m.rotate(self.computedRotation * 90)
        m.translate(-.5, -.5)
        m.scale(1 / self.pageWidth, 1 / self.pageHeight)

        source = self.transform().inverted()[0].mapRect(rect)
        return self._ic.image(source).transformed(m, Qt.TransformationMode.SmoothTransformation)

    def group(self) -> ImageContainer:
        return self._ic

    def mutex(self) -> ImageContainer:
        return self._ic


class ImageDocument(MultiSourceDocument):
    """A Document representing a group of images.

    A source may be a filename, a QIODevice or a QImage.

    """
    pageClass = ImagePage

    def createPages(self) -> Iterator[ImagePage]:
        for s in self.sources():
            if isinstance(s, QImage):
                if not s.isNull():
                    yield self.pageClass.fromImage(s, self.renderer)
            else:
                for p in self.pageClass.load(s, self.renderer):
                    yield p


class ImageRenderer(AbstractRenderer):
    def draw(
        self,
        page: ImagePage,
        painter: QPainter,
        key: Key,
        tile: Tile,
        paperColor: Optional[QColor] = None
    ):
        """Draw the specified tile of the page (coordinates in key) on painter."""
        # determine the part to draw; convert tile to viewbox
        source = self.map(key, page.pageRect()).mapRect(QRect(*tile))
        target = QRect(0, 0, tile.w, tile.h)
        if key.rotation & 1:
            target.setSize(target.size().transposed())
        image = page._ic.image(source).scaled(
            target.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter.drawImage(target, image)


# install a default renderer, so SvgPage can be used directly
ImagePage.renderer = ImageRenderer()
