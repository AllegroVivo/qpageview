import pytest
from PySide6.QtCore import QObject, QRect
from PySide6.QtPrintSupport import QPrinter

import qpageview.printing as printing


class _MockPage:
    def __init__(self, name="p", dpi=100.0):
        self.name = name
        self.dpi = dpi
        self.pageWidth = 200.0
        self.pageHeight = 100.0
        self.rotation = 0
        self.scaleX = 1.0
        self.scaleY = 1.0
        self.update_size_calls = []
        self.print_calls = 0
        self.copy_calls = 0

    def copy(self):
        self.copy_calls += 1
        cp = _MockPage(self.name, self.dpi)
        cp.pageWidth = self.pageWidth
        cp.pageHeight = self.pageHeight
        cp.rotation = self.rotation
        cp.scaleX = self.scaleX
        cp.scaleY = self.scaleY
        return cp

    def updateSize(self, dpi_x, dpi_y, zoom):
        self.update_size_calls.append((dpi_x, dpi_y, zoom))

    def print(self, _):
        self.print_calls += 1

class _MockPrinter:
    def __init__(self):
        self.full_page = None
        self.new_page_calls = 0
        self.abort_calls = 0
        self.logical_dpi_x = 100
        self.logical_dpi_y = 100
        self._page_rect = QRect(0, 0, 1000, 1000)

    def setFullPage(self, page):
        self.full_page = page

    def pageRect(self, _):
        return QRect(self._page_rect)

    def logicalDpiX(self):
        return self.logical_dpi_x

    def logicalDpiY(self):
        return self.logical_dpi_y

    def newPage(self):
        self.new_page_calls += 1
        return True

    def abort(self):
        self.abort_calls += 1
        return False

class _MockPainter:
    def __init__(self, device):
        self.device = device
        self.save_calls = 0
        self.restore_calls = 0
        self.transforms = []
        self.ended = False

    def save(self):
        self.save_calls += 1

    def restore(self):
        self.restore_calls += 1

    def setTransform(self, transform, combine):
        self.transforms.append((transform, combine))

    def end(self):
        self.ended = True
        return True

@pytest.fixture
def mp_painter(monkeypatch):
    created = {}

    def factory(device):
        p = _MockPainter(device)
        created["painter"] = p
        return p

    monkeypatch.setattr(printing, "QPainter", factory)
    return created

def test_print_job_set_page_page_list_numbers():
    printer = _MockPrinter()
    p1 = _MockPage("a")
    p2 = _MockPage("b")
    job = printing.PrintJob(printer, [p1, p2])  # type: ignore

    assert [n for n, _ in job.pageList] == [1, 2]
    assert all(page.update_size_calls[-1] == (page.dpi, page.dpi, 1.0) for _, page in job.pageList)

def test_print_job_set_page_list_tuples():
    printer = _MockPrinter()
    p1 = _MockPage("a")
    p2 = _MockPage("b")
    job = printing.PrintJob(printer, [(5, p1), (9, p2)])  # type: ignore

    assert [n for n, _ in job.pageList] == [5, 9]

def test_print_job_success_nd_signals(mp_painter):
    printer = _MockPrinter()
    pages = [_MockPage(f"p{i}") for i in range(3)]
    job = printing.PrintJob(printer, pages)  # type: ignore

    progress = []
    job.progress.connect(lambda pg_num, num, total: progress.append((pg_num, num, total)))

    result = job.work()

    assert result is True
    assert printer.full_page is True
    assert printer.new_page_calls == 2
    assert progress == [(1, 1, 3), (2, 2, 3), (3, 3, 3)]

    painter = mp_painter["painter"]
    assert painter.save_calls == 3
    assert painter.restore_calls == 3
    assert painter.ended is True

def test_print_job_interruption_abort(monkeypatch, mp_painter):
    printer = _MockPrinter()
    pages = [_MockPage(f"p{i}") for i in range(2)]
    job = printing.PrintJob(printer, pages)  # type: ignore

    call_count = {"n": 0}

    def abort_after_first_page():
        call_count["n"] += 1
        return call_count["n"] >= 2

    monkeypatch.setattr(job, "isInterruptionRequested", abort_after_first_page)

    result = job.work()

    assert result is False
    assert job.aborted is True
    assert printer.abort_calls == 1
    assert printer.new_page_calls == 0

def test_print_progress_dialog_initialization(qtbot):
    printer = _MockPrinter()
    pages = [_MockPage(f"p{i}") for i in range(2)]
    job = printing.PrintJob(printer, pages)  # type: ignore

    dialog = printing.PrintProgressDialog(job)
    qtbot.addWidget(dialog)

    assert dialog.minimum() == 0
    assert dialog.maximum() == 2
    assert dialog.labelText() == "Preparing to print..."

def test_print_progress_dialog_updates(qtbot):
    printer = _MockPrinter()
    pages = [_MockPage(f"p{i}") for i in range(3)]
    job = printing.PrintJob(printer, pages)  # type: ignore

    dialog = printing.PrintProgressDialog(job)
    qtbot.addWidget(dialog)

    dialog.showProgress(7, 2, 3)

    assert dialog.value() == 2
    assert dialog.labelText() == "Printing page 7 (2 of 3)..."

def test_print_progress_dialog_failed(monkeypatch, qtbot):
    printer = _MockPrinter()
    pages = [_MockPage("p1")]
    job = printing.PrintJob(printer, pages)  # type: ignore
    job.result = False
    job.aborted = False

    dialog = printing.PrintProgressDialog(job)
    qtbot.addWidget(dialog)

    called = {"n": 0}
    monkeypatch.setattr(dialog, "showErrorMessage", lambda: called.__setitem__("n", called["n"] + 1))

    dialog.jobFinished()

    assert called["n"] == 1

def test_print_progress_dialog_aborted(monkeypatch, qtbot):
    printer = _MockPrinter()
    pages = [_MockPage("p1")]
    job = printing.PrintJob(printer, pages)  # type: ignore
    job.result = False
    job.aborted = True

    dialog = printing.PrintProgressDialog(job)
    qtbot.addWidget(dialog)

    called = {"n": 0}
    monkeypatch.setattr(dialog, "showErrorMessage", lambda: called.__setitem__("n", called["n"] + 1))

    dialog.jobFinished()

    assert called["n"] == 0

def test_print_progress_dialog_canceled(qtbot):
    printer = _MockPrinter()
    pages = [_MockPage("p1")]
    job = printing.PrintJob(printer, pages)  # type: ignore

    dialog = printing.PrintProgressDialog(job)
    qtbot.addWidget(dialog)

    requested = {"n": 0}
    original = job.requestInterruption

    def wrapped():
        requested["n"] += 1
        return original()

    job.requestInterruption = wrapped

    dialog.canceled.emit()

    assert requested["n"] == 1
