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
Export Pages to different file formats.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, Union, Optional, Sequence

import os

from PySide6.QtCore import (
    QBuffer, QMimeData, QPoint, QSizeF, Qt, QUrl, QByteArray,
    QObject, QRect
)
from PySide6.QtGui import (
    QDrag, QGuiApplication, QImage, QPageSize, QPdfWriter, QColor,
    QPixmap
)

from . import util

if TYPE_CHECKING:
    from .typeinfo import MimeType
    from .page import AbstractPage
    from .document import AbstractSourceDocument
    from .render import AbstractRenderer
    from .image import ImageDocument
    from .svg import SvgDocument
    from .pdf import PdfDocument

TPage = TypeVar("TPage")

class AbstractExporter:
    """Base class to export a rectangular area of a Page to a file.

    Specialized subclasses implement each format.

    You instantiate a subclass with a Page and a rectangle. The rectangle may
    be None, to specify the full page. After instantiation, you can set
    attributes to configure the export. The following attributes are supported::

        resolution = 300
        autocrop = False
        oversample = 1
        grayscale = False
        paperColor = None

    After setting the attributes, you call one or more of save(), copyData(),
    copyFile(), mimeData() or tempFileMimeData(), which will trigger the export
    because they internally call data(), which caches its return value until
    setPage() is called again.

    Not all exporters support all attributes, the supportXXX attributes specify
    whether an attribute is supported or not.

    """
    # Typehints
    _page: AbstractPage
    _rect: QRect
    _result: Optional[Union[QByteArray, bytes]]
    _tempFile: Optional[str]
    _autoCropRect: Optional[QRect]
    _document: Optional[AbstractSourceDocument]
    _pixmap: Optional[QPixmap]

    # user settings:
    resolution: int = 300
    antialiasing: bool = True
    autocrop: bool = False
    oversample: int = 1
    grayscale: bool = False
    paperColor: QColor = None

    # properties of exporter:
    wantsVector: bool = True
    supportsResolution: bool = True
    supportsAntialiasing: bool = True
    supportsAutocrop: bool = True
    supportsOversample: bool = True
    supportsGrayscale: bool = True
    supportsPaperColor: bool = True

    mimeType: MimeType = "application/octet-stream"
    filename: str = ""
    defaultBasename: str = "document"
    defaultExt: str = ""

    def __init__(self, page: TPage, rect: Optional[QRect] = None):
        self.setPage(page, rect)

    def setPage(self, page: TPage, rect: Optional[QRect] = None):
        self._page = page.copy()
        if self._page.renderer:
            self._page.renderer = page.renderer.copy()
        self._rect = rect  # type: ignore - SP
        self._result = None   # where the exported object is stored
        self._tempFile = None
        self._autoCropRect = None
        self._document = None
        self._pixmap = None

    def page(self) -> TPage:
        """Return our page, setting the renderer to our preferences."""
        p = self._page.copy()
        p.paperColor = self.paperColor
        if self._page.renderer:
            p.renderer = self._page.renderer.copy()
            p.renderer.paperColor = self.paperColor
            p.renderer.antialiasing = self.antialiasing
        return p

    def autoCroppedRect(self) -> QRect:
        """Return the rect, auto-cropped if desired."""
        if not self.autocrop:
            return self._rect
        if self._autoCropRect is None:
            p = self._page
            dpiX = p.width / p.defaultSize().width() * p.dpi
            dpiY = p.height / p.defaultSize().height() * p.dpi
            image = p.image(self._rect, dpiX, dpiY)
            rect = util.autoCropRect(image)
            # add one pixel to prevent loosing small joins or curves etc
            rect = image.rect() & rect.adjusted(-1, -1, 1, 1)
            if self._rect is not None:
                rect.translate(self._rect.topLeft())
            self._autoCropRect = rect
        assert self._autoCropRect  # for type checker - SP
        return self._autoCropRect

    def export(self) -> Optional[Union[QByteArray, bytes]]:
        """Perform the export, based on the settings, and return the exported data object."""
        pass

    def successful(self) -> bool:
        """Return True when export was successful."""
        return self.data() is not None

    def data(self) -> Union[QByteArray, bytes]:
        """Return the export result, assuming it is binary data of the exported file."""
        if self._result is None:
            self._result = self.export()
        assert self._result  # for type checker - SP
        return self._result

    def document(self) -> AbstractSourceDocument:
        """Return a one-page Document to display the image to export.

        Internally calls createDocument(), and caches the result, setting the
        papercolor to the papercolor attribute if the exporter supports
        papercolor.

        """
        if self._document is None:
            doc = self._document = self.createDocument()
            if self.paperColor and self.paperColor.isValid():
                for p in doc.pages():
                    p.paperColor = self.paperColor
        assert self._document  # for type checker - SP
        return self._document

    def createDocument(self) -> AbstractSourceDocument:
        """Create and return a one-page Document to display the image to export."""
        pass

    # noinspection PyMethodMayBeStatic
    def renderer(self) -> Optional[AbstractRenderer]:
        """Return a renderer for the document(). By default, None is returned."""
        return None

    def copyData(self) -> None:
        """Copy the QMimeData() to the clipboard."""
        QGuiApplication.clipboard().setMimeData(self.mimeData())

    def mimeData(self) -> QMimeData:
        """Return a QMimeData() object representing the exported data."""
        data = QMimeData()
        data.setData(self.mimeType, self.data())
        return data

    def save(self, filename: str) -> None:
        """Save the exported image to a file."""
        with open(filename, "wb") as f:
            f.write(self.data())  # type: ignore - QByteArray and bytes are both buffered binary data, so this should work fine - SP

    def suggestedFilename(self) -> str:
        """Return a suggested file name for the file to export.

        The name is based on the filename (if set) and also contains the
        directory path. But the name will never be the same as the filename
        set in the filename attribute.

        """
        if self.filename:
            base = os.path.splitext(self.filename)[0]
            name = base + self.defaultExt
            if name == self.filename:
                name = base + "-export" + self.defaultExt
        else:
            name = self.defaultBasename + self.defaultExt
        return name

    def tempFilename(self) -> str:
        """Save data() to a tempfile and returns the filename."""
        if self._tempFile is None:
            if self.filename:
                basename = os.path.splitext(os.path.basename(self.filename))[0]
            else:
                basename = self.defaultBasename
            d = util.tempdir()
            fname = self._tempFile = os.path.join(d, basename + self.defaultExt)
            self.save(fname)
        assert self._tempFile  # for type checker - SP
        return self._tempFile

    def tempFileMimeData(self) -> QMimeData:
        """Save the exported image to a temp file and return a QMimeData object for the url."""
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(self.tempFilename())])
        return data

    def copyFile(self) -> None:
        """Save the exported image to a temp file and copy its name to the clipboard."""
        QGuiApplication.clipboard().setMimeData(self.tempFileMimeData())

    def pixmap(self, size: int = 100) -> QPixmap:
        """Return a small pixmap to use for dragging etc."""
        if self._pixmap is None:
            paperColor = self.paperColor if self.supportsPaperColor else None
            page = self.document().pages()[0]
            self._pixmap = page.pixmap(paperColor=paperColor)
        assert self._pixmap  # for type checker - SP
        return self._pixmap

    def drag(self, parent: QObject, mimeData: QMimeData) -> Qt.DropAction:
        """Called by dragFile and dragData. Execs a QDrag on the mime data."""
        d = QDrag(parent)
        d.setMimeData(mimeData)
        d.setPixmap(self.pixmap())
        d.setHotSpot(QPoint(-10, -10))
        return d.exec(Qt.DropAction.CopyAction)

    def dragData(self, parent: QObject) -> Qt.DropAction:
        """Start dragging the data. Parent can be any QObject."""
        return self.drag(parent, self.mimeData())

    def dragFile(self, parent: QObject) -> Qt.DropAction:
        """Start dragging the data. Parent can be any QObject."""
        return self.drag(parent, self.tempFileMimeData())


class ImageExporter(AbstractExporter):
    """Export a rectangular area of a Page (or the whole page) to an image."""
    wantsVector: bool = False
    defaultBasename: str = "image"
    defaultExt: str = ".png"

    def export(self) -> QImage:
        """Create the QImage representing the exported image."""
        res = self.resolution
        if self.oversample != 1:
            res *= self.oversample
        i = self.page().image(self._rect, res, res, self.paperColor)
        if self.oversample != 1:
            i = i.scaled(i.size() / self.oversample, mode=Qt.TransformationMode.SmoothTransformation)
        if self.grayscale:
            i = i.convertToFormat(QImage.Format.Format_Grayscale8)
        if self.autocrop:
            i = i.copy(util.autoCropRect(i))
        # needed for correct resolution metadata; see issue #44
        i.setDotsPerMeterX(int(res / .0254))
        i.setDotsPerMeterY(int(res / .0254))
        return i

    def image(self) -> QImage:
        return self.data()  # type: ignore - this works because export() returns a QImage, and data() caches the result of export() - SP

    def createDocument(self) -> ImageDocument:
        from . import image
        return image.ImageDocument([self.image()], self.renderer())

    def copyData(self) -> None:
        QGuiApplication.clipboard().setImage(self.image())

    def mimeData(self) -> QMimeData:
        data = QMimeData()
        data.setImageData(self.image())
        return data

    def save(self, filename: str) -> None:
        if not self.image().save(filename):
            raise OSError("Could not save image")


class SvgExporter(AbstractExporter):
    """Export a rectangular area of a Page (or the whole page) to an SVG file."""
    mimeType = "image/svg"
    supportsGrayscale = False
    supportsOversample = False
    defaultBasename = "image"
    defaultExt = ".svg"

    def export(self) -> Optional[Union[QByteArray, bytes]]:
        rect = self.autoCroppedRect()
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        success = self.page().svg(buf, rect, self.resolution, self.paperColor)
        buf.close()
        if success:
            return buf.data()

    def createDocument(self) -> SvgDocument:
        from . import svg
        return svg.SvgDocument([self.data()], self.renderer())


class PdfExporter(AbstractExporter):
    """Export a rectangular area of a Page (or the whole page) to a PDF file."""
    mimeType = "application/pdf"
    supportsGrayscale = False
    supportsOversample = False
    defaultExt = ".pdf"

    def export(self) -> Optional[Union[QByteArray, bytes]]:
        rect = self.autoCroppedRect()
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        success = self.page().pdf(buf, rect, self.resolution, self.paperColor)
        buf.close()
        if success:
            return buf.data()

    def createDocument(self) -> PdfDocument:
        from . import pdf
        return pdf.PdfDocument(self.data(), self.renderer())


def pdf(
    filename: str,
    pageList: Sequence[AbstractPage],
    resolution: int = 72,
    paperColor: Optional[QColor] = None
) -> None:
    """Export the pages in pageList to a PDF document.

    filename can be a string or any QIODevice. The pageList is a list of the
    Page objects to export.

    Normally vector graphics are rendered, but in cases where that is not
    possible, the resolution will be used to determine the DPI for the
    generated rendering.

    The computedRotation attribute of the pages is used to determine the
    rotation.

    Make copies of the pages if you run this function in a background thread.

    """
    pdf = QPdfWriter(filename)
    pdf.setCreator("qpageview")
    pdf.setResolution(resolution)

    for n, page in enumerate(pageList):
        # map to the original page
        source = page.pageRect()
        # scale to target size
        w = source.width() * page.scaleX
        h = source.height() * page.scaleY
        if page.computedRotation & 1:
            w, h = h, w
        targetSize = QSizeF(w, h)
        if n:
            pdf.newPage()
        layout = pdf.pageLayout()
        layout.setMode(layout.Mode.FullPageMode)
        layout.setPageSize(QPageSize(targetSize * 72.0 / page.dpi, QPageSize.Unit.Point))  # type: ignore[call-overload] - type checker is picking the wrong overload - SP
        pdf.setPageLayout(layout)
        # TODO handle errors?
        page.output(pdf, source, paperColor)
