from PyQt5.QtGui import QColor

COLORS = [
    QColor(0, 255, 0),  # 초록색
    QColor(0, 0, 255),  # 파란색
    QColor(255, 255, 0),  # 노란색
    QColor(0, 255, 255),  # 청록색 (시안)
    QColor(255, 0, 255),  # 마젠타
    QColor(255, 165, 0),  # 오렌지
    QColor(128, 0, 128),  # 보라
    QColor(0, 206, 209),  # 다크 터콰이즈
    QColor(255, 105, 180),  # 핫 핑크
    QColor(75, 0, 130),  # 인디고
    QColor(0, 128, 0),  # 진한 초록
    QColor(255, 69, 0),  # 레드 오렌지
    QColor(255, 215, 0),  # 골드
    QColor(0, 191, 255),  # 딥 스카이 블루
    QColor(0, 255, 127),  # 스프링 그린
    QColor(72, 61, 139),  # 다크 슬레이트 블루
    QColor(199, 21, 133),  # 미디엄 바이올렛 레드
    QColor(244, 164, 96),  # 샌디 브라운
    QColor(95, 158, 160),  # 캐딜락 블루
    QColor(30, 144, 255),  # 도저 블루
    QColor(124, 252, 0)  # 로운 그린
]

BUTTON_DEFAULT = """
    QPushButton {
        background-color: white;
        color: black;
        border-style: solid;
        border-width: 1px;
        border-color: lgihtgrey;
        border-radius: 5px;
        padding: 2px;
        margin : 2px;
    }
    QPushButton:hover {
        background-color: lightblue;
        color: black;
    }
"""

BUTTON_PUSHED = """
    QPushButton {
            background-color: lightblue;
            border-style: solid;
            border-width: 1px;
            border-color: lgihtgrey;
            border-radius: 5px;
            padding: 2px;
            margin : 2px;
        }
"""
LISTVIEW = """
    QListView::item:selected {
        background-color: lightblue;
        color: black;
    }
    QListView::item:!selected {
        background-color: white; 
        color: black;
        
    }
"""