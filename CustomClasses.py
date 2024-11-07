from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsView, QApplication, QGraphicsScene, QPlainTextEdit, QWidget, \
    QTextEdit, QGraphicsEllipseItem, QGraphicsItem, QStyle, QMenu, QAction
from PyQt5.QtCore import QRectF, Qt, QPointF, QRect, QStringListModel, QItemSelectionModel
from PyQt5.QtGui import QPen, QBrush, QPainter, QColor
from PyQt5.QtCore import QAbstractListModel, QModelIndex, Qt
from PyQt5.QtGui import QPainterPath

import main


class HandleItem(QGraphicsEllipseItem):
    def __init__(self, parent=None):
        super().__init__(-4, -4, 8, 8, parent)  # 핸들의 크기를 8x8로 설정
        self.parent = parent
        self.setBrush(QBrush(Qt.white))
        self.setPen(QPen((Qt.green), 1))
        self.setFlag(QGraphicsItem.ItemIsMovable)  # 핸들을 이동 가능하게 설정

        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges)  # 위치 변경 감지
        self.setZValue(10)
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # 새 위치를 가져옴
            new_pos = value
            # 특정 범위로 좌표를 제한
            if not (0 <= new_pos.x() <= self.parent.parent.width and 0 <= new_pos.y() <= self.parent.parent.height):
                # 좌표가 범위를 벗어난 경우, 가장 가까운 유효한 값으로 조정
                new_pos.setX(min(max(0, new_pos.x()), self.parent.parent.width))
                new_pos.setY(min(max(0, new_pos.y()), self.parent.parent.height))
            self.parentItem().updateRect()  # 핸들 위치 변경 시 사각형 업데이트
        return super().itemChange(change, value)


# [24.02.26 cy] undo 추가
class CustomRectItem(QGraphicsRectItem):
    handles = []
    border = 5

    def __init__(self, parent, file_name, color=QColor("green"), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.LeftButton | Qt.MiddleButton | Qt.RightButton)

        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)  # 위치 및 크기 변경 감지 활성화
        self.setFlag(super().ItemIsSelectable, True)
        # self.setFlag(super().ItemIsMovable, True)
        self.setFlag(super().ItemSendsGeometryChanges, True)

        # 처음 박스 좌표 저장
        self.startRect = None

        self.id = None
        self.setZValue(0)
        self.file_name = file_name
        self.parent = parent
        self.annotation = kwargs

        self.default_pen = color  # 기본 펜 설정
        self.hover_pen = QColor("red")  # 마우스를 올렸을 때의 펜 설정
        self.setPen(QPen(self.default_pen, self.border))

        self.joints = []
        self.setToolTip("OID : None")
        self.update()

    def to_default_color(self):
        self.setPen(QPen(self.default_pen, self.border))

    def selectedbox(self):
        self.setPen(QPen(self.hover_pen, self.border))
        self.addHandles()
        for item in self.parent.graphicsView.scene().items():
            if isinstance(item, CustomRectItem):
                item.to_default_color()
                item.setZValue(0)
        self.setPen(QPen(self.hover_pen, self.border))
        self.setZValue(1)

    def setID(self, id):
        self.id = id
        self.setToolTip("OID : " + str(self.id))

    # 호버 메서드
    def hoverEnterEvent(self, event):
        if self.parent.ModeChoice != 0:
            return
        """마우스가 사각형에 들어갈 때 호출되는 메서드."""
        self.setPen(QPen(self.hover_pen, self.border))
        super().hoverEnterEvent(event)

    # 처음 박스 크기 저장 함수
    def startResize(self):
        self.startRect = self.rect()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        if self.parent.ModeChoice != 0:
            return

        """마우스 버튼이 눌러질 때 호출되는 메서드."""
        if event.button() == Qt.LeftButton:
            self.parent.OIDItemClick(index=self.id)
            rows = self.parent.OIDmodel.rowCount()
            index = self.parent.OIDmodel.index(0, 0)
            selectionModel = self.parent.lv_OID.selectionModel()
            for row in range(rows):
                if self.parent.OIDmodel.data(self.parent.OIDmodel.index(row, 0), Qt.DisplayRole) == str(self.id):
                    index = self.parent.OIDmodel.index(row, 0)

            selectionModel.select(index, QItemSelectionModel.ClearAndSelect)

            self.selectedbox()
            rect = self.rect()
            self.parent.mainJson.setBox(self.id, [rect.x(), rect.y(), rect.width(), rect.height()],
                                        file_name=self.file_name)
            self.parent.updateAnnotationView(self.id)

    def hoverLeaveEvent(self, event):
        if self.parent.ModeChoice != 0:
            return
        """마우스가 사각형에서 나갈 때 호출되는 메서드."""
        self.to_default_color()
        super().hoverLeaveEvent(event)
        # self.setZValue(0)
        # self.update()

    def addHandles(self):
        # 이전 핸들 제거
        for handle in self.handles:
            self.scene().removeItem(handle)
        self.handles.clear()

        # 핸들 추가
        rect = self.rect()
        self.handles.append(self.createHandle(rect.topLeft()))
        # self.handles.append(self.createHandle(rect.topRight()))
        # self.handles.append(self.createHandle(rect.bottomLeft()))
        self.handles.append(self.createHandle(rect.bottomRight()))
        # 중간 지점 핸들 추가 (옵션)

    def createHandle(self, position):

        # 핸들 생성 및 추가
        handle = HandleItem(self)
        handle.setPos(position)
        return handle

    # 실제로 박스 크기가 조정되는 함수에 undo 커맨드 추가
    def updateRect(self):
        # 사각형의 크기를 핸들의 위치에 따라 조정
        if len(self.handles) < 2:
            return  # 핸들이 충분하지 않은 경우 업데이트하지 않음

        # 처음 크기 저장
        if not self.startRect:
            self.startResize()



        tl = self.handles[0].pos()
        br = self.handles[1].pos()
        newRect = QRectF(tl, br)

        if newRect != self.startRect:
            # 박스가 수정된 경우에만 undo 스택에 추가
            undoCommand = main.ResizeBoxCommand(self, self.startRect, newRect)
            self.parent.undoStack.push(undoCommand)

        self.setRect(newRect.normalized())

        rect = self.rect()

        self.parent.mainJson.setBox(self.id, [rect.x(), rect.y(), abs(rect.width()), abs(rect.height())],
                                    file_name=self.file_name)
        self.parent.updateAnnotationView(self.id)

    def paint(self, painter, option, widget):
        # 선택 상태일 때 점선 테두리를 표시하지 않음
        if self.isSelected():
            option.state &= ~QStyle.State_Selected  # 선택 상태 플래그 제거

        super().paint(painter, option, widget)

    def contextMenuEvent(self, event):
        mainMenu = QMenu()
        mainAction1 = mainMenu.addAction("Delete")

        # 선택된 액션에 대한 처리
        selected_action = mainMenu.exec_(event.screenPos())
        if selected_action == mainAction1:
            self.parent.removeBox(self.id)


# [24.02.26 cy] undo 추가
class CustomEllItem(QGraphicsEllipseItem):
    locList = ['left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist', 'left_hip',
               'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle', 'head', 'neck']
    radius = 5

    def __init__(self, parent, oid=0, loc=0, color=QColor('white'), rect=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setAcceptHoverEvents(True)  # 마우스 hover 이벤트를 활성화합니다.
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        # self.setFlag(super().ItemIsSelectable, True)
        self.parent = parent

        self.default_Brush = QBrush(color)  # 기본 펜 설정
        self.hover_Brush = QBrush(Qt.red)  # 마우스를 올렸을 때의 펜 설정
        self.setBrush(self.default_Brush)
        self.setRect(QRectF(-self.radius, -self.radius, self.radius * 2, self.radius * 2))

        self.setZValue(11)
        self.rect = rect
        self.oid = oid
        self.loc = loc
        self.setToolTip("OID : None, ID : None")
        self.parent.mainJson.setKeys(self.oid, self.loc, int(self.pos().x()), int(self.pos().y()))

        # 처음 키포인트 좌표 저장
        self.startPos = None


    def setColor(self, color=QColor('white')):
        self.default_Brush = QBrush(color)
        self.setBrush(self.default_Brush)

    def setIds(self, oid=0, loc=0):
        self.parent.mainJson.setKeys(self.oid, self.loc, 0, 0, 0)

        if oid == 0:
            oid = self.oid
        if loc == 0:
            loc = self.loc
        self.loc = loc
        self.oid = oid
        self.setToolTip("OID : " + str(self.oid) + ", ID : " + str(self.locList[self.loc]))
        self.parent.mainJson.setKeys(self.oid, self.loc, int(self.pos().x()), int(self.pos().y()))

    def hoverEnterEvent(self, event):
        self.setBrush(self.hover_Brush)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.default_Brush)
        super().hoverLeaveEvent(event)

    # 키포인트를 처음 클릭할 때 해당 좌표 저장
    def mousePressEvent(self, event):
        if self.shape().contains(event.pos()):
            self.startPos = self.pos()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.parent.ModeChoice != 0:
            return

        super().mouseMoveEvent(event)

    # 마우스 커서를 놓을 때 위치 저장
    def mouseReleaseEvent(self, event):
        endPos = self.pos()  # 최종 위치를 기록
        if self.startPos != endPos:
            # 시작 위치와 최종 위치가 다를 경우에만 커맨드를 추가
            command = main.MoveKeyPointCommand(self, self.startPos, endPos)
            self.parent.undoStack.push(command)
        # 마우스 놓은 후 필요한 업데이트 수행
        self.parent.updateAnnotationView(self.oid)
        self.parent.mainJson.setKeys(self.oid, self.loc, int(endPos.x()), int(endPos.y()))
        super().mouseReleaseEvent(event)


    def contextMenuEvent(self, event):
        mainMenu = QMenu()
        subMenu1 = QMenu("OID", mainMenu)
        subMenu2 = QMenu("Position", mainMenu)

        item_list = [self.parent.OIDmodel.data(self.parent.OIDmodel.index(row, 0), Qt.DisplayRole) for row in
                     range(self.parent.OIDmodel.rowCount())]
        subMenuAction1 = []
        # 서브메뉴에 액션 추가
        for item in item_list:
            subMenuAction1.append(subMenu1.addAction(str(item)))

        subMenuAction2 = []
        for item in self.locList:
            subMenuAction2.append(subMenu2.addAction(str(item)))

        # 메인 메뉴에 액션 및 서브메뉴 추가
        mainAction1 = mainMenu.addAction("Delete")
        mainMenu.addMenu(subMenu1)
        mainMenu.addMenu(subMenu2)

        selected_action = mainMenu.exec_(event.screenPos())

        # 선택된 액션에 대한 처리
        if selected_action == mainAction1:
            self.parent.removeKey(self.oid, self.loc)

        else:
            for i, action in enumerate(subMenuAction1):
                if selected_action == action:
                    self.setIds(oid=int(item_list[i]), loc=self.loc)
                    items = self.parent.graphicsView.scene().items()
                    if items:
                        for item in items:
                            if isinstance(item, CustomRectItem) and item.id == int(item_list[i]):
                                self.setColor(item.default_pen)

            for i, action in enumerate(subMenuAction2):
                if selected_action == action:
                    self.setIds(oid=self.oid, loc=int(i))

        self.parent.updateAnnotationView(self.oid)


    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.parent.updateAnnotationView(self.oid)
            # 새 위치를 가져옴
            new_pos = value
            # 특정 범위로 좌표를 제한

            if self.rect is None and not (0 <= new_pos.x() <= self.parent.width and 0 <= new_pos.y() <= self.parent.height):
                # 좌표가 범위를 벗어난 경우, 가장 가까운 유효한 값으로 조정
                new_pos.setX(min(max(0, new_pos.x()), self.parent.width))
                new_pos.setY(min(max(0, new_pos.y()), self.parent.height))

            elif self.rect is not None and not (self.rect.rect().x() <= new_pos.x() <= self.rect.rect().x()+self.rect.rect().width() and self.rect.rect().y() <= new_pos.y() <= self.rect.rect().height()):
                # 좌표가 범위를 벗어난 경우, 가장 가까운 유효한 값으로 조정
                new_pos.setX(min(max(self.rect.rect().x(), new_pos.x()), self.rect.rect().x() + self.rect.rect().width()))
                new_pos.setY(min(max(self.rect.rect().y(), new_pos.y()), self.rect.rect().y() + self.rect.rect().height()))

        return super().itemChange(change, value)


class MyGraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.scene().addItem(CustomRectItem(QRectF(0, 0, 100, 100)))


class CustomListModel(QStringListModel):
    def __init__(self, items=None, parent=None):
        super().__init__(parent)
        self.items = items or []
        self.setStringList(self.items)
        self.itemBackgroundColors = {}  # 배경색을 저장할 딕셔너리

    def data(self, index, role=Qt.DisplayRole, color=QBrush(QColor('white'))):
        if role == Qt.DisplayRole:
            # return self.items[index.row()]
            pass
        elif role == Qt.BackgroundRole:
            return self.itemBackgroundColors.get(index.row(), color)
        return super().data(index, role)

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.BackgroundRole:
            self.itemBackgroundColors[index.row()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return super().setData(index, value, role)
    # 필요한 경우 다른 메서드들 추가 및 오버라이드
