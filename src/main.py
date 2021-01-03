import sys

from PySide2.QtWidgets import QMainWindow, QApplication

from windows.main import MainWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(app)
    window.show()
    exit_code = app.exec_()
    sys.exit(exit_code)
