import sys
from PyQt5.QtWidgets import QApplication
from gui import HartGui

app = QApplication(sys.argv)
window = HartGui()
window.show()
sys.exit(app.exec_())