import sys
from PyQt5.QtWidgets import QApplication
from gui import HartGui


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HartGui()
    window.show()
    sys.exit(app.exec_()) 
