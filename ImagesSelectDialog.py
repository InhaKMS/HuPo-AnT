from PyQt5 import uic
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QDialog, QApplication, QVBoxLayout, QPushButton, QButtonGroup
import sys

from jsonControll import CrowdPoseJson


class ImagesSelectDialog(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi('ImagesSelectDialog.ui', self)
        self.radioButton_1.toggled.connect(self.toggleButtonState1)
        self.radioButton_2.toggled.connect(self.toggleButtonState2)
        self.le_start_1.setValidator(QRegExpValidator(QRegExp("[0-9]+"), self))
        self.le_end_1.setValidator(QRegExpValidator(QRegExp("[0-9]+"), self))
        self.le_start_2.setValidator(QRegExpValidator(QRegExp("[0-9]+"), self))
        self.le_num_2.setValidator(QRegExpValidator(QRegExp("[0-9]+"), self))
        self.lbl_message.setStyleSheet("color: red;")


        self.userInput1 = ''
        self.userInput2 = ''
        self.radioNum = 1

    def toggleButtonState1(self):
        if self.radioButton_1.isChecked():
            self.le_start_1.setEnabled(True)
            self.le_end_1.setEnabled(True)
            self.lbl_start_1.setEnabled(True)
            self.lbl_end_1.setEnabled(True)

            self.le_start_2.setEnabled(False)
            self.le_num_2.setEnabled(False)
            self.lbl_start_2.setEnabled(False)
            self.lbl_num_2.setEnabled(False)

            self.radioNum = 1

    def toggleButtonState2(self):
        if self.radioButton_2.isChecked():
            self.le_start_1.setEnabled(False)
            self.le_end_1.setEnabled(False)
            self.lbl_start_1.setEnabled(False)
            self.lbl_end_1.setEnabled(False)

            self.le_start_2.setEnabled(True)
            self.le_num_2.setEnabled(True)
            self.lbl_start_2.setEnabled(True)
            self.lbl_num_2.setEnabled(True)

            self.radioNum = 2

    def accept(self):
        try:
            if self.radioNum == 1:
                self.userInput1 = int(self.le_start_1.text())
                self.userInput2 = int(self.le_end_1.text())

                if not CrowdPoseJson.isExistImage(self.userInput2):
                    self.lbl_message.setText(str(self.userInput2) + "is not exist")

            if self.radioNum == 2:
                self.userInput1 = int(self.le_start_2.text())
                self.userInput2 = int(self.le_num_2.text())

            if not CrowdPoseJson.isExistImage(self.userInput1):
                self.lbl_message.setText(str(self.userInput1) + "is not exist")

        except ValueError:
            self.lbl_message.setText("Empty values exist")
            return



        super().accept()

    def reject(self):
        super().reject()
if __name__ == '__main__':
    app = QApplication(sys.argv)

    dialog = ImagesSelectDialog()
    dialog.show()

    sys.exit(app.exec_())
