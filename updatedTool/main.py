import json
import os
import sys
from PyQt5.QtCore import Qt, QEvent, QRectF, QObject
from PyQt5.QtGui import QPixmap, QTransform, QPen, QCursor, QBrush, QIcon, QColor
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtWidgets

import CustomClasses
import jsonControll
import styles
import crowd_index
from ImagesSelectDialog import ImagesSelectDialog

from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer

from PyQt5.QtGui import QKeySequence


# UI파일 연결
# 단, UI파일은 Python 코드 파일과 같은 디렉토리에 위치해야한다.


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


main_ui = resource_path('MainWindow.ui')
Ui_MainWindow = uic.loadUiType(main_ui)[0]  # ui 가져오기

dict_Image = {}  # using basename of images to key
CurImg = None  # 현재 표시되는 이미지 id = dict_Image의 key = image basename
CurObj = None  # 현재 클릭된 오브젝트 id

idVar = 2000000  # 새로 추가될 annotation id
colorVar = 0  # len(styles.COLORS)

# [24.05.29 cy] 객체 id 중복 해결
class UserInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User ID : ")

        layout = QVBoxLayout()

        self.label = QLabel("User ID : ")
        layout.addWidget(self.label)

        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(1)
        self.spinbox.setMaximum(100)
        layout.addWidget(self.spinbox)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

    def get_user_number(self):
        return self.spinbox.value()


# [24.02.19 cy] undo 커맨드 구현
class Command(QUndoCommand):
    def undo(self):
        pass

# [24.02.26 cy] 수정 undo 커맨드 추가
class ResizeBoxCommand(Command):
    def __init__(self, rectItem, oldRect, newRect, parent=None):
        super().__init__(parent)
        self.rectItem = rectItem
        self.oldRect = oldRect
        self.newRect = newRect

    def undo(self):
        self.rectItem.setRect(self.oldRect)
        self.rectItem.parent.updateAnnotationView(self.rectItem.id)
        self.rectItem.parent.mainJson.setBox(self.rectItem.id, [self.oldRect.x(), self.oldRect.y(), self.oldRect.width(), self.oldRect.height()], file_name=self.rectItem.file_name)
        self.rectItem.addHandles()
class MoveKeyPointCommand(Command):
    def __init__(self, keyPointItem, oldPos, newPos, parent=None):
        super().__init__(parent)
        self.keyPointItem = keyPointItem
        self.oldPos = oldPos
        self.newPos = newPos

    def undo(self):
        self.keyPointItem.setPos(self.oldPos)
        self.keyPointItem.parent.updateAnnotationView(self.keyPointItem.oid)

class MakeBoxCommand(Command):
    def __init__(self, window, rect_item, img_id, anno_id):
        super().__init__()
        self.window = window
        self.rect_item = rect_item
        self.img_id = img_id
        self.anno_id = anno_id

    def undo(self):
        self.window.undoMakeBox(self.rect_item, self.img_id, self.anno_id)


class RemoveBoxCommand(Command):
    def __init__(self, window, item, oid, box_info):
        super().__init__()
        self.window = window
        self.item = item
        self.oid = oid
        self.box_info = box_info  # 삭제되는 박스의 정보 저장

    def undo(self):
        self.window.undoRemoveBox(self.item, self.oid, self.box_info)


class MakeKeyCommand(Command):
    def __init__(self, window, x, y, pos, point_item, oid):
        super().__init__()
        self.window = window
        self.x = x
        self.y = y
        self.pos = pos
        self.point_item = point_item
        self.oid = oid

    def undo(self):
        self.window.undoMakeKey(self.point_item, self.oid, self.pos)


class RemoveKeyCommand(Command):
    def __init__(self, window, item, oid, loc, x, y):
        super().__init__()
        self.window = window
        self.item = item
        self.oid = oid
        self.loc = loc
        self.x = x
        self.y = y

    def undo(self):
        self.window.undoRemoveKey(self.item, self.oid, self.loc, self.x, self.y)


class Image:

    def __init__(self, path: str):
        # images info
        self.path = path
        self.file_name = os.path.basename(path)
        self.id = int(self.file_name.split('.')[0])
        self.crowdIndex = 0
        self.source = 'CrowdPoseTest'

        # annotation info
        self.idList = []

    def add_idList(self, anno_id: int):
        self.idList.append(anno_id)

    def delete_idList(self, anno_id: int):
        for i in range(len(self.idList)):
            if self.idList[i] == anno_id:
                del self.idList[i]
                break

        return -1

class GlobalShortcutFilter(QObject):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Delete:
                self.parent.removeBox(CurObj)

                return True  # 이벤트가 처리되었음을 나타냄
        return False
    
# [24.03.13 cy] 임계값 설정 창 추가
class CrowdIndexFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crowd Index Setting")
        layout = QVBoxLayout(self)
        
        # 최소 Crowd Index
        layout.addWidget(QLabel("Min Crowd Index:"))
        self.minSpinBox = QDoubleSpinBox()
        self.minSpinBox.setRange(0.0, 1.0)
        self.minSpinBox.setSingleStep(0.01)
        layout.addWidget(self.minSpinBox)
        
        # 최소 Crowd Index 조건 (이상, 초과)
        self.minInclusiveCheck = QCheckBox(">=")
        self.minExclusiveCheck = QCheckBox(">")
        self.minInclusiveCheck.setChecked(True)
        
        layout.addWidget(self.minInclusiveCheck)
        layout.addWidget(self.minExclusiveCheck)
        
        # 최대 Crowd Index
        layout.addWidget(QLabel("Max Crowd Index:"))
        self.maxSpinBox = QDoubleSpinBox()
        self.maxSpinBox.setRange(0.0, 10.0)
        self.maxSpinBox.setValue(10.0)
        self.maxSpinBox.setSingleStep(0.01)
        layout.addWidget(self.maxSpinBox)
        
        # 최대 Crowd Index 조건 (이하, 미만)
        self.maxInclusiveCheck = QCheckBox("<=")
        self.maxExclusiveCheck = QCheckBox("<")
        self.maxInclusiveCheck.setChecked(True)
        
        layout.addWidget(self.maxInclusiveCheck)
        layout.addWidget(self.maxExclusiveCheck)
        
        # 확인 버튼
        okButton = QPushButton("Check")
        okButton.clicked.connect(self.accept)
        layout.addWidget(okButton)

        # 체크박스 상호 배타적 연결 설정
        self.minInclusiveCheck.toggled.connect(lambda checked: self.minExclusiveCheck.setChecked(not checked))
        self.minExclusiveCheck.toggled.connect(lambda checked: self.minInclusiveCheck.setChecked(not checked))
        self.maxInclusiveCheck.toggled.connect(lambda checked: self.maxExclusiveCheck.setChecked(not checked))
        self.maxExclusiveCheck.toggled.connect(lambda checked: self.maxInclusiveCheck.setChecked(not checked))
        
    def get_values(self):
        return {
            'min_value': self.minSpinBox.value(),
            'min_inclusive': self.minInclusiveCheck.isChecked() and not self.minExclusiveCheck.isChecked(),
            'min_exclusive': self.minExclusiveCheck.isChecked() and not self.minInclusiveCheck.isChecked(),
            'max_value': self.maxSpinBox.value(),
            'max_inclusive': self.maxInclusiveCheck.isChecked() and not self.maxExclusiveCheck.isChecked(),
            'max_exclusive': self.maxExclusiveCheck.isChecked() and not self.maxInclusiveCheck.isChecked()
        }
    
class KeypointsThresholdDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keypoints Threshold Setting")
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Min Number of keypoints:"))
        self.thresholdSpinBox = QSpinBox()
        self.thresholdSpinBox.setRange(0, 14)
        layout.addWidget(self.thresholdSpinBox)
        
        okButton = QPushButton("Check")
        okButton.clicked.connect(self.accept)
        layout.addWidget(okButton)
        
    def get_threshold(self):
        return self.thresholdSpinBox.value()

# [24.03.28 cy] 임계값 설정 창 추가
class ObjectCountFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Num of Objects Setting")
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Min Num of Objects :"))
        self.minSpinBox = QSpinBox()
        self.minSpinBox.setRange(0, 100)  # 적절한 범위 설정
        layout.addWidget(self.minSpinBox)
        
        layout.addWidget(QLabel("Max Num of Objects :"))
        self.maxSpinBox = QSpinBox()
        self.maxSpinBox.setRange(0, 100)  # 적절한 범위 설정
        self.maxSpinBox.setValue(100)  # 초기 최대값 설정
        layout.addWidget(self.maxSpinBox)
        
        okButton = QPushButton("Check")
        okButton.clicked.connect(self.accept)
        layout.addWidget(okButton)
        
    def get_values(self):
        return self.minSpinBox.value(), self.maxSpinBox.value()
    
 # [24.03.29 cy] 임계값 설정 창 추가   
class BoundingBoxSizeFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bounding Box Size Setting")
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Min Bounding Box Size :"))
        self.minSpinBox = QSpinBox()
        self.minSpinBox.setRange(0, 500000)
        layout.addWidget(self.minSpinBox)
        
        layout.addWidget(QLabel("Max Bounding Box Size :"))
        self.maxSpinBox = QSpinBox()
        self.maxSpinBox.setRange(0, 500000)
        self.maxSpinBox.setValue(500000)
        layout.addWidget(self.maxSpinBox)
        
        okButton = QPushButton("Check")
        okButton.clicked.connect(self.accept)
        layout.addWidget(okButton)
        
    def get_values(self):
        return self.minSpinBox.value(), self.maxSpinBox.value()

class WindowClass(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.loc = 0
        self.setupUi(self)
        window_ico = resource_path('icon.JPG')
        self.setWindowIcon(QIcon(window_ico))  # 아이콘 설정
        self.showMaximized()


        # 중복 해결
        self.used_oids = set()

        self.undoStack = QUndoStack(self)
        self.setupShortcuts()

        self.mainJson = jsonControll.CrowdPoseJson(self)
        self.shortcutFilter = GlobalShortcutFilter(self)
        QApplication.instance().installEventFilter(self.shortcutFilter)

        self.ModeChoice = 0

        self.filemodel = CustomClasses.CustomListModel()
        self.lv_files.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lv_files.clicked.connect(self.filesItemClick)
        self.lv_files.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lv_files.customContextMenuRequested.connect(self.file_openMenu)
        self.lv_files.setStyleSheet(styles.LISTVIEW)

        self.OIDmodel = CustomClasses.CustomListModel()
        self.lv_OID.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.lv_OID.clicked.connect(self.OIDItemClick)
        self.lv_OID.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lv_OID.customContextMenuRequested.connect(self.OID_openMenu)
        self.lv_OID.setStyleSheet(styles.LISTVIEW)

        self.hs_box_border.valueChanged.connect(self.onBoxSliderValueChanged)
        self.hs_point_radius.valueChanged.connect(self.onPointSliderValueChanged)

        self.actionOpen_Images.triggered.connect(self.openImage)
        self.actionOpen_Directory.triggered.connect(self.openDirectory)

        # self.actionOpen_Video.triggered.connect(self.openVideo)

        # [24.05.15 cy] json 형식 변환 추가
        self.actionConvert_JSON_File.triggered.connect(self.convert_json_file)

        self.actionOpen_Label_File.triggered.connect(self.loadJson)
        self.actionSave.triggered.connect(self.saveJsonAs)
        self.actionSave_Filtered_CrowdIndex.triggered.connect(self.save_filtered_crowdindex)
        self.actionKeypoints.triggered.connect(self.save_filtered_keypoints)
        self.actionIscrowd.triggered.connect(self.remove_iscrowd)
        self.actionSave_Filtered_by_object_count.triggered.connect(self.save_filtered_by_object_count)
        self.actionSave_Filtered_by_boundingbox_size.triggered.connect(self.save_filtered_by_boundingbox_size)
        self.actionCalculate_CrowdPose.triggered.connect(self.newCalculate)
        self.actionUpdate_Keypoints.triggered.connect(self.update_number_of_keypoints)
        # [24.05.22 js] 중복된 객체 id 수정
        self.actionUpdate_Duplicate_IDs.triggered.connect(self.update_duplicate_ids)

        self.graphicsView.viewport().setCursor(QCursor(Qt.CrossCursor))

        # self.btn_format.clicked.connect(self.switchJsonFormat)
        self.btn_toggleEdit.clicked.connect(self.toggleEdit)
        self.btn_toggleBox.clicked.connect(self.toggleBox)
        self.btn_toggleKey.clicked.connect(self.toggleKeypoint)

        self.btn_toggleEdit.setStyleSheet(styles.BUTTON_DEFAULT)
        self.btn_toggleBox.setStyleSheet(styles.BUTTON_DEFAULT)
        self.btn_toggleKey.setStyleSheet(styles.BUTTON_DEFAULT)

        self.btn_toggleEdit.setShortcut('E')
        self.btn_toggleBox.setShortcut('B')
        self.btn_toggleKey.setShortcut('K')


        # [24.04.02 cy] 단축키로 저장 추가
        self.saveShortcut = QShortcut(QKeySequence.Save, self)
        self.saveShortcut.activated.connect(self.saveFile)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        self.btn__head_13.clicked.connect(self.button_makes_key)
        self.btn__neck_14.clicked.connect(self.button_makes_key)
        self.btn_left_shoulder_1.clicked.connect(self.button_makes_key)
        self.btn_right_shoulder_2.clicked.connect(self.button_makes_key)
        self.btn_left_elbow_3.clicked.connect(self.button_makes_key)
        self.btn_right_elbow_4.clicked.connect(self.button_makes_key)
        self.btn_left_wrist_5.clicked.connect(self.button_makes_key)
        self.btn_right_wrist_6.clicked.connect(self.button_makes_key)
        self.btn_left_hip_7.clicked.connect(self.button_makes_key)
        self.btn_right_hip_8.clicked.connect(self.button_makes_key)
        self.btn_left_knee_9.clicked.connect(self.button_makes_key)
        self.btn_right_knee_10.clicked.connect(self.button_makes_key)
        self.btn_left_ankle_11.clicked.connect(self.button_makes_key)
        self.btn_right_ankle_12.clicked.connect(self.button_makes_key)

        self.btn_left_shoulder_1.setShortcut('1')
        self.btn_right_shoulder_2.setShortcut('2')
        self.btn_left_elbow_3.setShortcut('3')
        self.btn_right_elbow_4.setShortcut('4')
        self.btn_left_wrist_5.setShortcut('5')
        self.btn_right_wrist_6.setShortcut('6')
        self.btn_left_hip_7.setShortcut('7')
        self.btn_right_hip_8.setShortcut('8')
        self.btn_left_knee_9.setShortcut('9')

        self.btn_right_knee_10.setShortcut('0')
        self.btn_left_ankle_11.setShortcut('-')
        self.btn_right_ankle_12.setShortcut('=')
        self.btn__head_13.setShortcut('q')
        self.btn__neck_14.setShortcut('w')

        for i in range(self.gridLayout.count()):
            widget = self.gridLayout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                widget.setStyleSheet(styles.BUTTON_DEFAULT)

        self.xDoubleSpinBox.valueChanged.connect(self.onBoxesValueChanged)
        self.yDoubleSpinBox.valueChanged.connect(self.onBoxesValueChanged)
        self.wDoubleSpinBox.valueChanged.connect(self.onBoxesValueChanged)
        self.hDoubleSpinBox.valueChanged.connect(self.onBoxesValueChanged)

        self.json_file_path = None
        self.odgt = dict()

        # self.getOriginSize()
        self.start_pos = None
        self.end_pos = None
        self.rect_item = None
        self.point_item = None

        self.graphicsView.viewport().installEventFilter(self)

    def show_user_input_dialog(self):
        # 중복 해결
        user_input_dialog = UserInputDialog()
        if user_input_dialog.exec_() == QDialog.Accepted:
            self.user_number = user_input_dialog.get_user_number()
        else:
            # 유저 번호 입력을 취소한 경우 기본값으로 설정
            self.user_number = 1
        
        self.show()

    # [24.05.29 cy] 중복 id 해결
    def generate_unique_oid(self):
        oid = max(self.used_oids, default=0) % 1000000 + 1
        while (self.user_number * 1000000 + oid) in self.used_oids:
            oid = (oid + 1) % 1000000
        self.used_oids.add(self.user_number * 1000000 + oid)
        return self.user_number * 1000000 + oid

    # [24.05.08 cy] 내부 바운딩 박스 선택이 가능하도록 esc 클릭 시 바운딩 박스 선택 해제
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.deselectAllBoxes()
        super().keyPressEvent(event)

    def deselectAllBoxes(self):
        for item in self.graphicsView.scene().items():
            if isinstance(item, CustomClasses.CustomRectItem):
                item.setSelected(False)
                item.to_default_color()
                item.setZValue(0)
        self.lv_OID.clearSelection()

    def eventFilter(self, obj, event):

        self.graphicsView.viewport().setMouseTracking(True)
        self.lbl_boxCnt.setText("Objects : " + str(self.OIDmodel.rowCount()))
        if self.graphicsView.scene() is not None:

            if obj == self.graphicsView.viewport() and self.ModeChoice == 0:
                if event.type() == QEvent.MouseMove:
                    # 마우스의 좌표 얻기
                    pos = event.pos()
                    scene_pos = self.graphicsView.mapToScene(pos)
                    # 좌표 출력
                    self.lbl_cursorX.setText("X : " + str(round(scene_pos.x(), 4)))
                    self.lbl_cursorY.setText("Y : " + str(round(scene_pos.y(), 4)))

            elif obj == self.graphicsView.viewport() and self.ModeChoice == 1:
                if event.type() == QEvent.MouseMove:
                    # 마우스의 좌표 얻기
                    pos = event.pos()
                    scene_pos = self.graphicsView.mapToScene(pos)
                    # 좌표 출력
                    self.lbl_cursorX.setText("X : " + str(round(scene_pos.x(), 4)))
                    self.lbl_cursorY.setText("Y : " + str(round(scene_pos.y(), 4)))

                if event.type() == QEvent.MouseButtonPress:
                    if event.button() == Qt.LeftButton:
                        self.start_pos = self.graphicsView.mapToScene(event.pos())
                        self.end_pos = self.graphicsView.mapToScene(event.pos())
                        self.rect_item = CustomClasses.CustomRectItem(self, CurImg, color=styles.COLORS[
                            colorVar % len(styles.COLORS)])
                        self.rect_item.setPen(QPen(Qt.red))
                        self.graphicsView.scene().addItem(self.rect_item)

                        #self.lbl_bboxH.setText("H : 0")
                        #self.lbl_bboxW.setText("W : 0")

                elif event.type() == QEvent.MouseMove:
                    if event.buttons() & Qt.LeftButton and self.start_pos is not None:
                        self.end_pos = self.graphicsView.mapToScene(event.pos())
                        self.updateRectangle()

                        #self.lbl_bboxW.setText("W : " + str(round(abs(self.start_pos.x() - scene_pos.x()))))
                        #self.lbl_bboxH.setText("H : " + str(round(abs(self.start_pos.y() - scene_pos.y()))))
                        return False

                elif event.type() == QEvent.MouseButtonRelease:
                    if event.button() == Qt.LeftButton and self.start_pos is not None:
                        # self.end_pos = self.graphicsView.mapToScene(event.pos())
                        self.rect_item.to_default_color()
                        if True:
                            if self.start_pos.x() < 0:
                                self.start_pos.setX(0)
                            elif self.start_pos.x() > self.width:
                                self.start_pos.setX(self.width)
                            if self.start_pos.y() < 0:
                                self.start_pos.setY(0)
                            elif self.start_pos.y() > self.height:
                                self.start_pos.setY(self.height)

                            if self.end_pos.x() < 0:
                                self.end_pos.setX(0)
                            elif self.end_pos.x() > self.width:
                                self.end_pos.setX(self.width)
                            if self.end_pos.y() < 0:
                                self.end_pos.setY(0)
                            elif self.end_pos.y() > self.height:
                                self.end_pos.setY(self.height)

                            if self.start_pos.x() > self.end_pos.x():
                                tmp = self.start_pos.x()
                                self.start_pos.setX(self.end_pos.x())
                                self.end_pos.setX(tmp)
                            if self.start_pos.y() > self.end_pos.y():
                                tmp = self.start_pos.y()
                                self.start_pos.setY(self.end_pos.y())
                                self.end_pos.setY(tmp)

                        self.updateRectangle()
                        self.makeBox()
                        self.updateAnnotationView(idVar - 1)

                        #[24.11.08 HJ] 키포인트와 박스 버튼 동시에 눌려있을 때 버그 생기는 부분 주석처리
                        #self.start_pos = None
                        #self.end_pos = None
                        #self.rect_item = None
                        return False

            elif obj == self.graphicsView.viewport() and self.ModeChoice == 2:

                if event.type() == QEvent.MouseMove:
                    # 마우스의 좌표 얻기
                    pos = event.pos()
                    scene_pos = self.graphicsView.mapToScene(pos)
                    # 좌표 출력
                    self.lbl_cursorX.setText("X : " + str(round(scene_pos.x(), 4)))
                    self.lbl_cursorY.setText("Y : " + str(round(scene_pos.y(), 4)))

                if event.type() == QEvent.MouseButtonPress:
                    if event.button() == Qt.LeftButton:

                        self.start_pos = self.graphicsView.mapToScene(event.pos())
                        if True:  # 박스의 경계에 찍히도록 하기 위해서 start_pos.x(), y() 등등을 <0이 아닌 박스의 width, height로 고쳐주면 될 것 같음
                            if self.start_pos.x() < 0:
                                self.start_pos.setX(0)
                            elif self.start_pos.x() > self.width:
                                self.start_pos.setX(self.width)
                            if self.start_pos.y() < 0:
                                self.start_pos.setY(0)
                            elif self.start_pos.y() > self.height:
                                self.start_pos.setY(self.height)

                        self.makeKey(self.start_pos.x(), self.start_pos.y(), self.loc)
                        self.updateAnnotationView(idVar)

                        return True

        return super().eventFilter(obj, event)

    def setupShortcuts(self):
        # Ctrl+Z를 사용한 Undo 설정
        self.undoShortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undoShortcut.activated.connect(self.undoStack.undo)

    def makeBox(self):  # add dict_Image, rect_item, Json
        #global idVar
        global colorVar
        oid = self.generate_unique_oid()

        #dict_Image[CurImg].add_idList(idVar)
        #self.rect_item.setID(idVar)

        dict_Image[CurImg].add_idList(oid)
        self.rect_item.setID(oid)

        self.mainJson.setBox(file_name=CurImg, OID=oid, box=[int(self.start_pos.x()),
                                                               int(self.start_pos.y()),
                                                               int(self.end_pos.x() - self.start_pos.x()),
                                                               int(self.end_pos.y() - self.start_pos.y())]
                             )
        self.populateOID()
        self.OIDItemClick(oid)
        colorVar += 1

        command = MakeBoxCommand(self, self.rect_item, CurImg, oid)
        #self.newCalculate()
        self.undoStack.push(command)

        # self.mainJson.setBox(file_name=CurImg, OID=idVar, box=[int(self.start_pos.x()),
        #                                                        int(self.start_pos.y()),
        #                                                        int(self.end_pos.x() - self.start_pos.x()),
        #                                                        int(self.end_pos.y() - self.start_pos.y())]
        #                      )
        # CurObj = idVar
        # self.populateOID()
        # self.OIDItemClick(CurObj)
        # idVar += 1
        # colorVar += 1

        # # [24.02.19 cy] undo 커맨드 추가
        # command = MakeBoxCommand(self, self.rect_item, CurImg, idVar - 1)
        # self.newCalculate()
        # self.undoStack.push(command)

    # [24.02.19 cy] undo 함수 구현
    def undoMakeBox(self, rect_item, img_id, anno_id):

        # 생성된 box id 제거
        dict_Image[img_id].delete_idList(anno_id)
        rect_item.handles.clear()
        try:
            self.graphicsView.scene().removeItem(rect_item)
            self.mainJson.delObj(anno_id)
            self.populateOID()
            #self.newCalculate()
        except RuntimeError:
            print('''
            Traceback (most recent call last):
                self.graphicsView.scene().removeItem(rect_item)
            RuntimeError: wrapped C/C++ object of type CustomRectItem has been deleted
            ''')

    def button_makes_key(self):
        apply_stylesheet_to_buttons(self)
        self.toggleKeypoint()
        self.sender().setStyleSheet(styles.BUTTON_PUSHED)
        self.loc = int(self.sender().objectName().split('_')[3]) - 1

    def makeKey(self, x: object, y: object, pos):
        color = QColor("white")
        rectitem = None
        items = self.graphicsView.scene().items()

        if items:
            for item in items:
                if isinstance(item, CustomClasses.CustomRectItem) and item.id == CurObj:
                    color = item.default_pen
                    rectitem = item
        self.point_item = CustomClasses.CustomEllItem(self, color=color, rect=rectitem)
        self.point_item.setIds(CurObj, pos)
        self.point_item.setPos(x, y)
        self.graphicsView.scene().addItem(self.point_item)
        self.mainJson.setKeys(CurObj, pos, int(x), int(y))
        self.updateAnnotationView(CurObj)

        # [24.03.13 cy] 키포인트 추가 후 자동으로 num_keypoints 업데이트
        #self.update_number_of_keypoints()
        #self.newCalculate()

        # [24.02.19 cy] undo 커맨드 추가
        command = MakeKeyCommand(self, x, y, pos, self.point_item, CurObj)
        self.undoStack.push(command)

    # [24.02.19 cy] undo 함수 구현
    def undoMakeKey(self, point_item, oid, pos):

        # 생성된 키 포인트 제거
        try:
            self.graphicsView.scene().removeItem(point_item)
            self.mainJson.delKey(oid, pos)
            self.updateAnnotationView(oid)

            # [24.03.13 cy] undo 후 자동으로 num_keypoints 업데이트
            #self.update_number_of_keypoints()
            #self.newCalculate()
        except RuntimeError:
            print('wrapped C/C++ object of type CustomEllItem has been deleted')

    def removeBox(self, oid=None, all=False):
        CustomClasses.CustomRectItem.handles.clear()
        items = self.graphicsView.scene().items()

        # if oid is None:
        #     oid = CurObj
        #
        for row in range(self.OIDmodel.rowCount()):
            if self.OIDmodel.data(self.OIDmodel.index(row, 0), Qt.DisplayRole) == str(oid):
                self.OIDmodel.removeRow(row)

        # [24.02.20 cy] undo 커맨드 추가
        box_info = None  # 바운딩 박스 정보를 저장할 변수

        if items:
            for item in items:
                if (isinstance(item, CustomClasses.CustomRectItem) and item.id == oid) or all:
                    box_info = self.mainJson.getBox(item.id)  # 삭제된 박스 정보 get
                    self.graphicsView.scene().removeItem(item)
                    self.mainJson.delObj(item.id)
                    dict_Image[CurImg].delete_idList(item.id)
                    self.removeKey(item.id)
                    break
            # [24.02.20 cy] undo 커맨드 추가
            if box_info:
                #self.newCalculate()
                command = RemoveBoxCommand(self, item, oid, box_info)
                self.undoStack.push(command)

    # [24.02.20 cy] undo 함수 구현
    def undoRemoveBox(self, item, oid, box_info):
        if item.scene() is None:
            self.graphicsView.scene().addItem(item)
        dict_Image[CurImg].add_idList(oid)
        self.mainJson.setBox(OID=oid, box=box_info, file_name=CurImg)
        self.populateOID()
        #self.newCalculate()
        # self.filesItemClick(index=self.filemodel.index(self.filemodel.stringList().index(CurImg), 0))

    def removeKey(self, oid, loc=-1, all=False):
        self.mainJson.delKey(oid, loc)
        items = self.graphicsView.scene().items()

        if items:
            for item in items:
                if loc == -1:
                    item.loc = loc
                if (isinstance(item, CustomClasses.CustomEllItem) and item.oid == oid and item.loc == loc) or all:
                    x, y = item.pos().x(), item.pos().y()  # [24.02.19 cy] 삭제된 키포인트 좌표 저장
                    self.graphicsView.scene().removeItem(item)
                    self.updateAnnotationView(oid)

                    # [24.03.13 cy] 키포인트 삭제 후 자동으로 num_keypoints 업데이트
                    #self.update_number_of_keypoints()
                    #self.newCalculate()

                    # [24.02.20 cy] undo 커맨드 추가
                    command = RemoveKeyCommand(self, item, oid, loc, x, y)
                    self.undoStack.push(command)

    # [24.02.20 cy] undo 함수 구현
    def undoRemoveKey(self, item, oid, loc, x, y):

        if item.scene() is None:
            self.graphicsView.scene().addItem(item)

        self.mainJson.setKeys(oid, loc, int(x), int(y))
        self.updateAnnotationView(oid)

        # [24.03.13 cy] undo 후 자동으로 num_keypoints 업데이트
        #self.update_number_of_keypoints()
        #self.newCalculate()

    def updateRectangle(self):

        rect = QRectF(self.start_pos, self.end_pos).normalized()
        self.rect_item.setRect(rect)

    def toggleEdit(self):
        self.ModeChoice = 0
        apply_stylesheet_to_buttons(self)
        self.btn_toggleEdit.setStyleSheet(styles.BUTTON_PUSHED)

    def toggleBox(self):
        self.ModeChoice = 1
        apply_stylesheet_to_buttons(self)
        self.btn_toggleBox.setStyleSheet(styles.BUTTON_PUSHED)

    def toggleKeypoint(self):
        self.ModeChoice = 2
        apply_stylesheet_to_buttons(self)
        self.btn_toggleKey.setStyleSheet(styles.BUTTON_PUSHED)

    def populateList(self, text):
        # QStringListModel 생성 및 데이터 설정
        name_list = [v.file_name for v in dict_Image.values()]
        self.filemodel.setStringList(sorted(name_list))

        # QListView에 model 설정
        self.lv_files.setModel(self.filemodel)

    def populateOID(self):

        # QStringListModel 생성 및 데이터 설정
        self.OIDmodel.setStringList(map(str, dict_Image[CurImg].idList))

        # QListView에 model 설정
        self.lv_OID.setModel(self.OIDmodel)

    def filesItemClick(self, index):
        global CurImg  # 현재 표시되는 이미지 id = dict_Image의 key
        global CurObj  # 현재 클릭된 오브젝트 id

        # 클릭된 아이템의 인덱스를 가져옵니다.
        imgkey = self.filemodel.data(index, Qt.DisplayRole)
        CurImg = imgkey
        CurObj = None
        self.loadImage(dict_Image[imgkey].path)

        objs = self.getJsonByImageID(dict_Image[CurImg].id)
        if not len(objs) == 0:
            self.updateAnnotationView(objs[0]["id"])

        self.setRectsbyJson()
        self.populateOID()
        for i in self.mainJson.after_json["images"]:
            if i["id"] == dict_Image[CurImg].id:
                self.lbl_crowdindex.setText("CrowdIndex : " + str(i["crowdIndex"]))
                break

    def OIDItemClick(self, index):
        if self.OIDmodel.rowCount() == 0:
            return
        if isinstance(index, int):
            rows = self.OIDmodel.rowCount()
            for row in range(rows):
                if self.OIDmodel.data(self.OIDmodel.index(row, 0), Qt.DisplayRole) == str(index):
                    index = self.OIDmodel.index(row, 0)

        oid = int(self.OIDmodel.data(index, Qt.DisplayRole))

        global CurObj
        CurObj = oid

        cr = crowd_index.get_crowd_ratio(
            [o for o in self.mainJson.before_json["annotations"] if o["image_id"] == dict_Image[CurImg].id])
        for id, ratio in cr:
            found = False
            if id == oid:
                self.lbl_crowdratio.setText(str(ratio))
                found = True
                break
            if found is False:
                self.lbl_crowdratio.setText('0.0')
        self.updateAnnotationView(oid)
        for item in self.graphicsView.scene().items():
            self.OIDmodel.setData(index, QBrush(QColor("white")), Qt.BackgroundRole)
            if isinstance(item, CustomClasses.CustomRectItem):
                if item.id == oid:
                    self.OIDmodel.setData(index, QBrush(QColor("lightblue")), Qt.BackgroundRole)
                    item.selectedbox()

    def updateAnnotationView(self, oid: int = None):
        if oid is None:
            box = [0, 0, 0, 0]
        else:
            box = self.mainJson.getBox(oid)
            self.setKeypointsSpinBoxes(oid)

        self.xDoubleSpinBox.setValue(box[0])
        self.yDoubleSpinBox.setValue(box[1])
        self.wDoubleSpinBox.setValue(box[2])
        self.hDoubleSpinBox.setValue(box[3])

    def setKeypointsSpinBoxes(self, OID: int):
        data = self.getJsonByOID(OID)
        if len(data) == 0:
            return

        data = data[0]
        self.lbl_pointCnt.setText(
            "Keypoints : " + str(len([i for i in range(2, len(data["keypoints"]), 3) if data["keypoints"][i] != 0])))
        self.left_shoulderSpinBox.setValue(data["keypoints"][0])
        self.left_shoulderSpinBox_2.setValue(data["keypoints"][1])

        self.right_shoulderSpinBox.setValue(data["keypoints"][3])
        self.right_shoulderSpinBox_2.setValue(data["keypoints"][4])

        self.left_elbowSpinBox.setValue(data["keypoints"][6])
        self.left_elbowSpinBox_2.setValue(data["keypoints"][7])

        self.right_elbowSpinBox.setValue(data["keypoints"][9])
        self.right_elbowSpinBox_2.setValue(data["keypoints"][10])

        self.left_wristSpinBox.setValue(data["keypoints"][12])
        self.left_wristSpinBox_2.setValue(data["keypoints"][13])

        self.right_wristSpinBox.setValue(data["keypoints"][15])
        self.right_wristSpinBox_2.setValue(data["keypoints"][16])

        self.left_hipSpinBox.setValue(data["keypoints"][18])
        self.left_hipSpinBox_2.setValue(data["keypoints"][19])

        self.right_hipSpinBox.setValue(data["keypoints"][21])
        self.right_hipSpinBox_2.setValue(data["keypoints"][22])

        self.left_kneeSpinBox.setValue(data["keypoints"][24])
        self.left_kneeSpinBox_2.setValue(data["keypoints"][25])

        self.right_kneeSpinBox.setValue(data["keypoints"][27])
        self.right_kneeSpinBox_2.setValue(data["keypoints"][28])

        self.left_ankleSpinBox.setValue(data["keypoints"][30])
        self.left_ankleSpinBox_2.setValue(data["keypoints"][31])

        self.right_ankleSpinBox.setValue(data["keypoints"][33])
        self.right_ankleSpinBox_2.setValue(data["keypoints"][34])

        self.headSpinBox.setValue(data["keypoints"][36])
        self.headSpinBox_2.setValue(data["keypoints"][37])

        self.neckSpinBox.setValue(data["keypoints"][39])
        self.neckSpinBox_2.setValue(data["keypoints"][40])

    def file_openMenu(self, position):
        # 컨텍스트 메뉴 생성
        menu = QMenu()

        # 삭제 메뉴 항목 추가
        deleteAction = menu.addAction("Delete")
        action = menu.exec_(self.lv_files.mapToGlobal(position))

        # 삭제 액션 처리
        if action == deleteAction:
            indexes = self.lv_files.selectedIndexes()
            if indexes:
                index = indexes[0]
                self.filemodel.removeRow(index.row())

    def OID_openMenu(self, position):
        # 컨텍스트 메뉴 생성
        menu = QMenu()

        # 삭제 메뉴 항목 추가
        deleteAction = menu.addAction("Delete")
        action = menu.exec_(self.lv_OID.mapToGlobal(position))

        # 삭제 액션 처리
        if action == deleteAction:
            indexes = self.lv_OID.selectedIndexes()
            if indexes:
                index = indexes[0]
                oid = int(self.OIDmodel.data(self.OIDmodel.index(index.row(), 0), Qt.DisplayRole))
                self.removeBox(oid)
                # self.OIDmodel.removeRow(index.row())

    def populateListWithDirectory(self, dir):
        self.filemodel.removeRows(0, self.filemodel.rowCount())
        for file in sorted(os.listdir(dir)):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.filemodel.insertRow(self.filemodel.rowCount())
                self.filemodel.setData(self.filemodel.index(self.filemodel.rowCount() - 1), file)
        self.lv_files.setModel(self.filemodel)

    def openImage(self):
        global CurImg  # 현재 표시되는 이미지 id = dict_Image의 key
        global CurObj  # 현재 클릭된 오브젝트 id

        file_paths, _ = QFileDialog.getOpenFileNames(self, 'Select Files', '', 'Images (*.png *.xpm *.jpg)')
        if file_paths:
            # self.dialog.show()
            for i, file_path in enumerate(file_paths):
                m = 0
                n = int(100 / (i + 1))
                if m != n:
                    m = n
                    # self.dialog.update_progress(m)
                dict_Image[os.path.basename(file_path)] = Image(file_path)  # ch

            CurImg = os.path.basename(file_paths[0])
            CurObj = None

            self.populateList(file_path)
            self.loadImage(file_paths[0])
        print("openImage() - dict_Images : ", dict_Image)

    def openDirectory(self):
        global CurImg  # 현재 표시되는 이미지 id = dict_Image의 key
        global CurObj  # 현재 클릭된 오브젝트 id

        dir = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        if dir:
            self.populateListWithDirectory(dir)
            file_paths = [os.path.join(dir, file) for file in os.listdir(dir) if
                          file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]
            if file_paths:
                # self.dialog.show()
                for i, file_path in enumerate(file_paths):
                    m = 0
                    n = int(100 / (i + 1))
                    if m != n:
                        m = n
                        # self.dialog.update_progress(m)
                    dict_Image[os.path.basename(file_path)] = Image(file_path)  # ch

                CurImg = os.path.basename(file_paths[0])
                CurObj = None

                # self.populateList(file_path)
                self.loadImage(file_paths[0])

    def loadImage(self, image_path):
        # 이미지 파일을 로드합니다.
        pixmap = QPixmap(image_path)

        # QGraphicsScene을 생성하고 이미지를 표시할 QGraphicsPixmapItem을 생성합니다.
        scene = QGraphicsScene()
        pixmap_item = QGraphicsPixmapItem(pixmap)
        scene.addItem(pixmap_item)

        # graphicsView에 QGraphicsScene을 설정합니다.
        self.graphicsView.setScene(scene)
        CustomClasses.CustomRectItem.handles = []

        self.graphicsView.resetTransform()
        self.getOriginSize()
        self.lbl_filename.setText(image_path)
        self.lbl_ImageSize.setText(
            "Origin Size : " + str(self.width) + " x " + str(self.height))
        self.lbl_CurrentSize.setText(
            "Current Size : " + str(self.width) + " x " + str(self.height))
        self.lbl_Scale.setText("Scale : 100%")

    def getOriginSize(self):
        # Graphics View에 표시된 이미지의 원래 크기 얻기
        scene = self.graphicsView.scene()
        items = scene.items()
        original_size = -1
        for item in items:
            if isinstance(item, QGraphicsPixmapItem):
                pixmap = item.pixmap()
                original_size = pixmap.size()
                break
        self.width = original_size.width()
        self.height = original_size.height()

    def wheelEvent(self, event):
        # Ctrl 키를 누르고 있을 때만 이미지 크기를 조정합니다.
        if event.modifiers() == Qt.ControlModifier:
            # 현재 이미지의 크기를 가져옵니다.
            current_size = self.graphicsView.transform().m11()
            angle = event.angleDelta().y() / 120  # 휠 동작의 각도를 가져옵니다.
            scale_factor = 1.1 ** angle  # 이미지 크기를 조정하는 비율 계산

            # 원본 이미지의 가로세로 크기

            # 이미지를 비율로 조정합니다.
            new_size = current_size * scale_factor
            new_transform = QTransform().scale(new_size, new_size)
            self.graphicsView.setTransform(new_transform)
            self.getOriginSize()
            self.lbl_ImageSize.setText("Origin Size : " + str(self.width) + " x " + str(self.height))
            self.lbl_CurrentSize.setText(
                "Current Size : " + str(round(self.width * new_size)) + " x " + str(round(self.height * new_size)))
            self.lbl_Scale.setText("Scale : " + str(round(new_size * 100)) + "%")

            # 이미지의 중심을 기준으로 조정하기 위해 view의 중심을 계산합니다.
            scene_pos = self.graphicsView.mapToScene(self.graphicsView.viewport().rect().center())
            view_pos = self.graphicsView.mapFromScene(scene_pos)
            self.graphicsView.centerOn(view_pos)

        else:
            # Ctrl 키를 누르지 않은 경우에는 원래의 wheelEvent 동작을 수행합니다.
            super().wheelEvent(event)

    def setRectsbyJson(self):
        if CurImg is None:
            return
        items = self.graphicsView.scene().items()
        CustomClasses.CustomRectItem.handles.clear()
        if items:
            for item in items:
                if isinstance(item, CustomClasses.CustomRectItem) or isinstance(item, CustomClasses.CustomEllItem):
                    self.graphicsView.scene().removeItem(item)

        global colorVar
        colorVar = 0

        data = self.getJsonByImageID(dict_Image[CurImg].id)

        dict_Image[CurImg].idList = list(set(dict_Image[CurImg].idList) | set([item["id"] for item in data]))

        for i in data:
            rect = CustomClasses.CustomRectItem(self, CurImg, color=styles.COLORS[colorVar % len(styles.COLORS)])
            rect.setRect(i["bbox"][0], i["bbox"][1], i["bbox"][2], i["bbox"][3])
            rect.setID(int(i["id"]))
            rect.setZValue(0)

            self.graphicsView.scene().addItem(rect)
            self.setKeysbyJson(i)
            colorVar += 1
        self.populateOID()

    def setKeysbyJson(self, data):
        if isinstance(data, list):
            for i in data:
                for j in range(0, len(i["keypoints"]), 3):
                    point = CustomClasses.CustomEllItem(self)
                    point.setPos(i["keypoints"][j], i["keypoints"][j + 1])
                    self.graphicsView.scene().addItem(point)
        elif isinstance(data, dict):
            items = self.graphicsView.scene().items()
            if items:
                for item in items:
                    if isinstance(item, CustomClasses.CustomRectItem) and item.id == int(data["id"]):
                        color = item.default_pen
            for j in range(0, len(data["keypoints"]), 3):
                if data["keypoints"][j + 2] == 0:
                    continue

                point = CustomClasses.CustomEllItem(self, color=color)
                point.setPos(data["keypoints"][j], data["keypoints"][j + 1])
                point.oid = int(data['id'])
                point.loc = j // 3
                point.setToolTip("OID : " + str(point.oid) + ", ID : " + str(point.locList[point.loc]))

                self.graphicsView.scene().addItem(point)

    def getJsonByImageID(self, imgid):
        if isinstance(imgid, str):
            imgid = int(os.path.basename(imgid).split('.')[0])
        return [item for item in self.mainJson.after_json["annotations"] if item["image_id"] == imgid]

    def getJsonByOID(self, OID: int):

        data = self.getJsonByImageID(CurImg)
        return [item for item in data if item["id"] == OID]

    def saveJsonAs(self):
        # JSON 파일 저장 대화 상자 열기
        new_file_path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "JSON Files (*.json)")

        try:
            with open(new_file_path, 'w') as file:
                json.dump(self.mainJson.after_json, file)
                self.mainJson.before_json = self.mainJson.after_json
                # [24.04.02 cy] 단축키로 저장 추가
                self.json_file_path = new_file_path
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An error occurred while saving the file:\n{str(e)}")

    # [24.05.15 cy] json 형식 변환 추가
    def convert_json_file(self):
        # 선택한 형식에 따라 json 파일 변환 처리
        format_menu = QMenu(self)
        posetrack_action = format_menu.addAction("PoseTrack")
        coco_action = format_menu.addAction("COCO")
        crowdhuman_action = format_menu.addAction("CrowdHuman")
        action = format_menu.exec_(QCursor.pos())

        if action == posetrack_action:
            input_file, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
            if input_file:
                # 저장할 파일 경로 선택
                output_file, _ = QFileDialog.getSaveFileName(self, "Save Converted JSON File", "", "JSON Files (*.json)")
                if output_file:
                    self.process_posetrack_json(input_file, output_file)
        elif action == coco_action:
            input_file, _ = QFileDialog.getOpenFileName(self, "Select JSON File", "", "JSON Files (*.json)")
            if input_file:
                # 저장할 파일 경로 선택
                output_file, _ = QFileDialog.getSaveFileName(self, "Save Converted JSON File", "", "JSON Files (*.json)")
                if output_file:
                    self.process_coco_json(input_file, output_file)
        elif action == crowdhuman_action:
            QMessageBox.information(self, "Not Implemented", "CrowdHuman format conversion is not implemented yet.")

    def process_posetrack_json(self, input_file, output_file):
        try:
            with open(input_file, 'r') as file:
                data = json.load(file)

            # 'images' 섹션 처리
            for image in data['images']:
                # 'file_name'에서 파일 이름만 추출
                image['file_name'] = os.path.basename(image['file_name'])
                # 'ignore_regions_x'와 'ignore_regions_y' 제거
                image.pop('ignore_regions_x', None)
                image.pop('ignore_regions_y', None)

            # 변경된 데이터를 새 파일로 저장
            with open(output_file, 'w') as file:
                json.dump(data, file, indent=4)

            QMessageBox.information(self, "Conversion Complete", f"JSON file has been converted and saved to {output_file}")
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", f"An error occurred during conversion:\n{str(e)}")

    def process_coco_json(self, input_file, output_file):
        try:
            with open(input_file, 'r') as file:
                coco_data = json.load(file)

                crowdpose_data = {
                    "images": [],
                    "annotations": [],
                    "categories": [
                        {
                            "supercategory": "person",
                            "id": 1,
                            "name": "person",
                            "keypoints": [
                                "left_shoulder",
                                "right_shoulder",
                                "left_elbow",
                                "right_elbow",
                                "left_wrist",
                                "right_wrist",
                                "left_hip",
                                "right_hip",
                                "left_knee",
                                "right_knee",
                                "left_ankle",
                                "right_ankle",
                                "head",
                                "neck"
                            ],
                            "skeleton": [
                                [16, 14], [14, 12], [17, 15], [15, 13], [12, 13], [6, 12],
                                [7, 13], [6, 7], [6, 8], [7, 9], [8, 10], [9, 11]
                            ]
                        }
                    ]
                }

                image_id_map = {}

                for coco_image in coco_data["images"]:
                    image_id = int(os.path.splitext(coco_image["file_name"])[0])
                    image_id_map[coco_image["id"]] = image_id
                    
                    crowdpose_image = {
                        "file_name": coco_image["file_name"],
                        "id": image_id,
                        "height": coco_image["height"],
                        "width": coco_image["width"],
                        "crowdIndex": 0
                    }
                    
                    crowdpose_data["images"].append(crowdpose_image)

                for coco_annotation in coco_data["annotations"]:
                    if coco_annotation["num_keypoints"] == 0:
                        continue
                    
                    keypoints = coco_annotation["keypoints"]
                    
                    # Map COCO keypoints to CrowdPose keypoints
                    crowdpose_keypoints = [0] * (14 * 3)  # Initialize keypoints with 0s

                    # Mapping: COCO index -> CrowdPose index
                    keypoint_mapping = {
                        5: 0,    # left_shoulder
                        6: 1,    # right_shoulder
                        7: 2,    # left_elbow
                        8: 3,    # right_elbow
                        9: 4,    # left_wrist
                        10: 5,   # right_wrist
                        11: 6,   # left_hip
                        12: 7,   # right_hip
                        13: 8,   # left_knee
                        14: 9,   # right_knee
                        15: 10,  # left_ankle
                        16: 11   # right_ankle
                    }

                    for coco_index, crowdpose_index in keypoint_mapping.items():
                        coco_keypoint = keypoints[coco_index * 3 : coco_index * 3 + 3]
                        if coco_keypoint[2] > 0:
                            crowdpose_keypoints[crowdpose_index * 3] = coco_keypoint[0]
                            crowdpose_keypoints[crowdpose_index * 3 + 1] = coco_keypoint[1]
                            crowdpose_keypoints[crowdpose_index * 3 + 2] = coco_keypoint[2]

                    if keypoints[3*0] > 0:
                        crowdpose_keypoints[12 * 3] = keypoints[3*0]
                        crowdpose_keypoints[12 * 3 + 1] = keypoints[3*0+1]
                        crowdpose_keypoints[12 * 3 + 2] = keypoints[3*0+2]

                    if keypoints[3*5] > 0 and keypoints[3*6] > 0:
                        # 5번째와 6번째 keypoints가 둘 다 있으면, neck의 위치와 점수를 계산
                        neck_x = (keypoints[3*5] + keypoints[3*6]) / 2
                        neck_y = (keypoints[3*5+1] + keypoints[3*6+1]) / 2
                        neck_score = (keypoints[3*5+2] + keypoints[3*6+2]) / 2
                        crowdpose_keypoints[13 * 3] = neck_x
                        crowdpose_keypoints[13 * 3 + 1] = neck_y
                        crowdpose_keypoints[13 * 3 + 2] = neck_score
                    else:
                        # 5번째 또는 6번째 keypoints 중 하나라도 없으면, neck 정보를 0으로 설정
                        crowdpose_keypoints[13 * 3] = 0
                        crowdpose_keypoints[13 * 3 + 1] = 0
                        crowdpose_keypoints[13 * 3 + 2] = 0

                    crowdpose_annotation = {
                        "num_keypoints": sum(1 for i in range(2, len(crowdpose_keypoints), 3) if crowdpose_keypoints[i] > 0),
                        "iscrowd": coco_annotation["iscrowd"],
                        "keypoints": crowdpose_keypoints,
                        "image_id": image_id_map[coco_annotation["image_id"]],
                        "bbox": coco_annotation["bbox"],
                        "category_id": 1,
                        "id": len(crowdpose_data["annotations"]) + 1
                    }
                    
                    crowdpose_data["annotations"].append(crowdpose_annotation)

                with open(output_file, 'w') as f:
                    json.dump(crowdpose_data, f, indent=4)

            QMessageBox.information(self, "Conversion Complete", f"JSON file has been converted and saved to {output_file}")
        except Exception as e:
            QMessageBox.critical(self, "Conversion Error", f"An error occurred during conversion:\n{str(e)}")

    # [24.04.02 cy] 단축키로 저장 추가
    def saveFile(self):
        if self.json_file_path is None:
            new_file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "JSON Files (*.json)")
            if new_file_path:
                self.json_file_path = new_file_path
        
        if self.json_file_path:
            try:
                with open(self.json_file_path, 'w') as file:
                    json.dump(self.mainJson.after_json, file)
                    self.mainJson.before_json = self.mainJson.after_json
                
                # 저장 완료 시 하단 바에 메세지 출력
                self.statusBar.showMessage("Save complete", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"An error occurred while saving the file:\n{str(e)}")

    # [24.03.13 cy] 임계값을 통한 필터링 메서드 추가
    def save_filtered_crowdindex(self):
        dialog = CrowdIndexFilterDialog(self)
        result = dialog.exec_()
        
        if result:
            values = dialog.get_values()
            
            new_file_path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON Files (*.json)")
            if new_file_path:  
                try:
                    filtered_json = self.mainJson.filtered_by_crowd_index(
                        min_value=values['min_value'],
                        min_inclusive=values['min_inclusive'],
                        min_exclusive=values['min_exclusive'],
                        max_value=values['max_value'],
                        max_inclusive=values['max_inclusive'],
                        max_exclusive=values['max_exclusive']
                    )
                    with open(new_file_path, 'w') as file:
                        json.dump(filtered_json, file, indent=4)
                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Save Error:\n{str(e)}")

    def save_filtered_keypoints(self):
        dialog = KeypointsThresholdDialog(self)
        result = dialog.exec_()
        
        if result:
            threshold = dialog.get_threshold()
            
            new_file_path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON Files (*.json)")
            if new_file_path:  
                try:
                    filtered_json = self.mainJson.filtered_by_keypoints(threshold)

                    with open(new_file_path, 'w') as file:
                        json.dump(filtered_json, file, indent=4)
                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Save Error:\n{str(e)}")

    # [24.03.13 cy] iscrowd=1 제거
    # [24.05.28 cy] 함수 수정
    def remove_iscrowd(self):
        
        try:
            self.mainJson.remove_iscrowd()
            self.setRectsbyJson()  # 변경된 JSON 데이터를 반영하여 화면 업데이트
            QMessageBox.information(self, "Filterinf Complete", "remove is_crowd=1.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Filtering Error:\n{str(e)}")
    
        # new_file_path, _ = QFileDialog.getSaveFileName(self, "is_crowd가 1인 객체를 제거한 파일 저장", "", "JSON Files (*.json)")
        # if new_file_path:
        #     try:
        #         filtered_json = self.mainJson.remove_iscrowd()
        #         with open(new_file_path, 'w') as file:
        #             json.dump(filtered_json, file, indent=4)
        #     except Exception as e:
        #         QMessageBox.critical(self, "저장 오류", f"Save Error:\n{str(e)}")

    # def update_number_of_keypoints(self):
    #     for ann in self.mainJson.after_json['annotations']:
    #         # 키포인트 배열에서 3번째마다 나오는 v 값이 0이 아닌 경우를 세어 num_keypoints를 업데이트
    #         num_keypoints = sum(1 for i in range(2, len(ann['keypoints']), 3) if ann['keypoints'][i] > 0)
    #         ann['num_keypoints'] = num_keypoints

    def update_number_of_keypoints(self):
        updated_images = set()
        updated_objects = 0
        updated_keypoints = 0
        
        for ann in self.mainJson.after_json['annotations']:
            # 키포인트 배열에서 3번째마다 나오는 v 값이 0이 아닌 경우를 세어 num_keypoints를 업데이트
            num_keypoints = sum(1 for i in range(2, len(ann['keypoints']), 3) if ann['keypoints'][i] > 0)
            
            if ann['num_keypoints'] != num_keypoints:
                updated_keypoints += abs(ann['num_keypoints'] - num_keypoints)
                ann['num_keypoints'] = num_keypoints
                updated_objects += 1
                updated_images.add(ann['image_id'])
        
        QMessageBox.information(self, "Update Result", f"{len(updated_images)} Images, {updated_objects} Objects, {updated_keypoints} Keypoints Updated")

    # [24.05.22 js] 객체들의 중복된 id를 새로운 id로 변경
    def update_duplicate_ids(self):
        new_file_path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON Files (*.json)")
        if new_file_path:
            try:
                filtered_json, duplicate_ids, duplicate_images = self.mainJson.update_duplicate_ids()
                with open(new_file_path, 'w') as file:
                    json.dump(filtered_json, file, indent=4)

                QMessageBox.information(self, "Update Result", f"Duplicate IDs : {len(duplicate_ids)}\nImages with Duplicate IDs : {len(duplicate_images)}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Save Error:\n{str(e)}")

    # [24.03.28 cy] 객체 개수로 필터링
    def save_filtered_by_object_count(self):
        dialog = ObjectCountFilterDialog(self)
        result = dialog.exec_()
        
        if result:
            min_count, max_count = dialog.get_values()
            
            new_file_path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON Files (*.json)")
            if new_file_path:
                try:
                    filtered_json = self.mainJson.filtered_by_object_count(min_count, max_count)
                    with open(new_file_path, 'w') as file:
                        json.dump(filtered_json, file, indent=4)
                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Save Error:\n{str(e)}")

    # [24.03.29 cy] 바운딩 박스 크기로 필터링
    def save_filtered_by_boundingbox_size(self):
        dialog = BoundingBoxSizeFilterDialog(self)
        result = dialog.exec_()
        
        if result:
            min_size, max_size = dialog.get_values()
            
            new_file_path, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON Files (*.json)")
            if new_file_path:
                try:
                    filtered_json = self.mainJson.filtered_by_boundingbox_size(min_size, max_size)
                    with open(new_file_path, 'w') as file:
                        json.dump(filtered_json, file, indent=4)
                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Save Error:\n{str(e)}")


    def onBoxesValueChanged(self, value):
        pass

    # 중복 해결
    def update_used_oids(self):
        self.used_oids.clear()
        for annotation in self.mainJson.after_json['annotations']:
            self.used_oids.add(annotation['id'])

    def loadJson(self):
        self.mainJson.loadJson()
        self.update_used_oids()
        #global idVar
        #idVar = self.mainJson.getLastOIDnum()

    def imagesSelect(self):
        dialog = ImagesSelectDialog()

        if dialog.exec_() == QDialog.Accepted:
            print(f'Input: {dialog.userInput1}, {dialog.userInput2}')

    def onBoxSliderValueChanged(self, value):
        CustomClasses.CustomRectItem.border = value
        self.setRectsbyJson()

    def onPointSliderValueChanged(self, value):
        CustomClasses.CustomEllItem.radius = value
        self.setRectsbyJson()

    def newCalculate(self):
        for image in self.mainJson.after_json["images"]:
            image_id = image['id']
            objs = [i for i in self.mainJson.after_json["annotations"] if i["image_id"] == image_id]
            image["crowdIndex"] = crowd_index.get_crowd_index(objs)
        self.setRectsbyJson()
    # 크라우드 인덱스 값을 계산 버튼 누를 시 재계산해주는 함수

    # def Fit


def apply_stylesheet_to_buttons(widget, indent=0):
    # widget의 자식 위젯들을 순회
    for child in widget.children():
        # 자식이 QPushButton이면 정보 출력
        if isinstance(child, QPushButton):
            child.setStyleSheet(styles.BUTTON_DEFAULT)
        # 자식이 컨테이너 위젯이면 재귀적으로 탐색
        apply_stylesheet_to_buttons(child, indent + 1)


if __name__ == "__main__":
    # QApplication : 프로그램을 실행시켜주는 클래스
    app = QApplication(sys.argv)

    # WindowClass의 인스턴스 생성
    myWindow = WindowClass()

     # 시작 화면 표시
    splash = QSplashScreen(QPixmap('logo.jpg'))
    splash.setWindowFlag(Qt.WindowStaysOnTopHint)
    splash.show()

    # 이벤트 루프 시작
    app.processEvents()

    # 시작 화면이 표시되는 시간 설정
    QTimer.singleShot(2000, splash.close)
    #QTimer.singleShot(2000, myWindow.show)
    QTimer.singleShot(2000, myWindow.show_user_input_dialog)

    # 프로그램 화면을 보여주는 코드
    #myWindow.show()

    # 프로그램을 이벤트루프로 진입시키는(프로그램을 작동시키는) 코드
    app.exec_()
