from __future__ import annotations

import sys

import qpageview

from PySide6.QtWidgets import QApplication

def main() -> int:

    app = QApplication([])

    view = qpageview.View()
    view.resize(800, 600)
    view.show()
    view.loadPdf("Test.pdf")

    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
