# -*- coding: utf-8 -*-
#
# This file is part of the qpageview package.
#
# Copyright (c) 2016 - 2019 by Wilbert Berendsen
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
A page that can display an SVG document.

"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union, Iterator, Type

from PySide6.QtCore import QRectF, Qt, QByteArray
from PySide6.QtGui import QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

from .document import MultiSourceDocument
from .locking import lock
from .page import AbstractRenderedPage
from .render import AbstractRenderer

if TYPE_CHECKING:
    from .render import Key, Tile

class SvgPage(AbstractRenderedPage):
    """A page that can display an SVG document."""

    dpi: float = 90.0

    def __init__(self, svgrenderer: QSvgRenderer, renderer: Optional[AbstractRenderer] = None):
        super().__init__(renderer)
        self._svg: QSvgRenderer = svgrenderer
        self.pageWidth: int = svgrenderer.defaultSize().width()
        self.pageHeight: int = svgrenderer.defaultSize().height()
        self._viewBox: QRectF = svgrenderer.viewBoxF()

    @classmethod
    def load(
        cls,
        filename: Union[str, QByteArray],
        renderer: Optional[AbstractRenderer] = None
    ) -> Iterator[SvgPage]:
        """Load an SVG document from filename, which may also be a QByteArray.

        Yields only one Page instance, as SVG currently supports one page per
        file. If the file can't be loaded by the underlying QSvgRenderer,
        no Page is yielded.

        """
        r = QSvgRenderer()
        if r.load(filename):  # type: ignore - typechecker can't figure out the overloads - SP
            yield cls(r, renderer)

    def mutex(self) -> QSvgRenderer:
        return self._svg

    def group(self) -> QSvgRenderer:
        return self._svg


class SvgDocument(MultiSourceDocument):
    """A Document representing a group of SVG files."""
    pageClass: Type[SvgPage] = SvgPage

    def createPages(self) -> Iterator[SvgPage]:
        return self.pageClass.loadFiles(self.sources(), self.renderer)


class SvgRenderer(AbstractRenderer):
    """Render SVG pages."""
    def setRenderHints(self, painter: QPainter) -> None:
        """Sets the renderhints for the painter we want to use."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, self.antialiasing)

    def draw(
        self,
        page: SvgPage,
        painter: QPainter,
        key: Key,
        tile: Tile,
        paperColor: Optional[QColor] = None
    ) -> None:
        """Draw the specified tile of the page (coordinates in key) on painter."""
        # determine the part to draw; convert tile to viewbox
        viewbox = self.map(key, page._viewBox).mapRect(QRectF(*tile))
        target = QRectF(0, 0, tile.w, tile.h)
        if key.rotation & 1:
            target.setSize(target.size().transposed())
        with lock(page._svg):
            page._svg.setViewBox(viewbox)
            # we must specify the target otherwise QSvgRenderer scales to the
            # unrotated image
            painter.save()
            painter.setClipRect(target, Qt.ClipOperation.IntersectClip)
            # QSvgRenderer seems to set antialiasing always on anyway... :-)
            self.setRenderHints(painter)
            page._svg.render(painter, target)
            painter.restore()
            page._svg.setViewBox(page._viewBox)


# install a default renderer, so SvgPage can be used directly
SvgPage.renderer = SvgRenderer()
