from typing import Iterator

import pytest
from qpageview.document import (
    Document, AbstractSourceDocument,
    SingleSourceDocument, MultiSourceDocument
)


class _MockPage:
    def __init__(self, pg_num):
        self.page_num = pg_num
        self._links = []

    def links(self):
        return self._links

class _MockLink:
    def __init__(self, url):
        self.url = url
        self.area = "area_" + url

### Document Tests ###
def test_document_pages():
    doc = Document()
    assert doc.count() == 0

    page1 = _MockPage(1)
    page2 = _MockPage(2)
    doc._pages = [page1, page2]  # type: ignore

    assert doc.count() == 2
    pages = doc.pages()
    assert pages[0] is page1
    assert pages[1] is page2

def test_document_clear():
    doc = Document([_MockPage(1)])  # type: ignore
    doc.clear()
    assert doc.count() == 0

def test_document_urls_empty():
    doc = Document()
    assert doc.urls() == {}

def test_document_urls():
    page1 = _MockPage(1)
    page2 = _MockPage(2)

    link1 = _MockLink("https://example.com")
    page1._links.append(link1)

    doc = Document([page1, page2])  # type: ignore
    urls = doc.urls()

    assert "https://example.com" in urls
    assert 0 in urls["https://example.com"]  # Page1 is page number 0
    assert link1.area in urls["https://example.com"][0]


### AbstractSourceDocument Tests ###
class _MockSourceDocument(AbstractSourceDocument):
    def __init__(self, pages):
        super().__init__()
        self.pages_to_create = pages
        self.createPages_called = 0

    def createPages(self):
        self.createPages_called += 1
        return iter(self.pages_to_create)


def test_abstract_source_document_lazy_pages():
    doc = _MockSourceDocument([_MockPage(1), _MockPage(2)])
    assert doc.pages_to_create is not None
    assert doc.createPages_called == 0

    pages = doc.pages()

    assert doc.createPages_called == 1
    assert len(pages) == 2


def test_abstract_source_document_caching():
    doc = _MockSourceDocument([_MockPage(1), _MockPage(2)])

    pages1 = doc.pages()
    pages2 = doc.pages()

    assert doc.createPages_called == 1  # createPages should only be called once
    assert pages1 is pages2  # Should be the same cached list

def test_abstract_source_document_invalidate():
    doc = _MockSourceDocument([_MockPage(1), _MockPage(2)])

    pages1 = doc.pages()
    doc.invalidate()
    doc.pages_to_create = [_MockPage(3), _MockPage(4)]  # Change the pages to create after invalidating
    pages2 = doc.pages()

    assert doc.createPages_called == 2  # createPages should be called again after invalidate
    assert pages1 is not pages2  # Should be a new list of pages after invalidate
    assert pages2[0].page_num == 3  # type: ignore


### SingleSourceDocument Tests ###
class _MockSingleSourceDocument(SingleSourceDocument):
    def __init__(self, source):
        super().__init__(source)
        self.createPages_called = 0

    def createPages(self):
        self.createPages_called += 1
        return iter([_MockPage(1)])

def test_single_source_document_keeps_source():
    doc = _MockSingleSourceDocument("file.pdf")
    assert doc.source() == "file.pdf"

def test_single_source_document_set_source():
    doc = _MockSingleSourceDocument("file.pdf")
    doc.pages()  # Force load

    doc.setSource("new_file.pdf")
    assert doc.source() == "new_file.pdf"

def test_single_source_document_filename():
    doc = _MockSingleSourceDocument("file.pdf")
    assert doc.filename() == "file.pdf"

    doc2 = _MockSingleSourceDocument(b"bytes")  # type: ignore
    assert doc2.filename() == ""  # Not a string source should return empty filename


### MultiSourceDocument Tests ###
class _MockMultiSourceDocument(MultiSourceDocument):
    def __init__(self, sources):
        super().__init__(sources)
        self.createPages_called = 0

    def createPages(self):
        self.createPages_called += 1
        return iter([_MockPage(i) for i in range(len(self._sources))])


def test_multi_source_document_sources():
    doc = _MockMultiSourceDocument(["file1.pdf", "file2.pdf"])
    assert doc.sources() == ["file1.pdf", "file2.pdf"]

def test_multi_source_document_set_sources():
    doc = _MockMultiSourceDocument(["file1.pdf", "file2.pdf"])
    doc.pages()  # Force load

    doc.setSources(["new_file1.pdf", "new_file2.pdf"])
    assert doc.sources() == ["new_file1.pdf", "new_file2.pdf"]

def test_multi_source_document_filenames():
    doc = _MockMultiSourceDocument(["file1.pdf", "file2.pdf"])
    assert doc.filenames() == ["file1.pdf", "file2.pdf"]

    doc2 = _MockMultiSourceDocument(["file1.pdf", b"bytes"])  # type: ignore
    assert doc2.filenames() == ["file1.pdf", ""]
