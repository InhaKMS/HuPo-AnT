import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QDialog, QProgressBar
from PyQt5.QtCore import QTimer
from qtpy import uic

dialog_class = uic.loadUiType("Dialog.ui")[0]

class ProgressDialog(QDialog, dialog_class):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.progressBar.setValue(0)
        self.btn_cancel.clicked.connect(self.reject)

    def update_progress(self, n):
        value = self.progressBar.value()
        value += n
        self.progressBar.setValue(value)
        if value < 100:
            pass
        else:
            self.accept()  # 프로그래스바가 100%에 도달하면 Dialog를 닫습니다.

