import sys
import os
import math
import threading

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLineEdit, QListWidget,
    QVBoxLayout, QListWidgetItem, QLabel, QHBoxLayout, QPushButton
)
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QRectF, pyqtSignal
)
from PyQt5.QtGui import QPainter, QPen, QColor, QPolygonF, QBrush

from searcher import search_files, open_in_explorer
from icon_locator import get_desktop_icon_positions
from window_finder import get_newest_explorer_rect


THEMES = {
    "light": {
        "bg": "rgba(255, 255, 255, 245)",
        "border": "rgba(0, 0, 0, 0.08)",
        "input_bg": "rgba(0, 0, 0, 0.04)",
        "input_border": "rgba(0, 0, 0, 0.12)",
        "input_focus_border": "rgba(230, 60, 60, 0.5)",
        "input_text": "#1a1a1a",
        "input_placeholder": "#999",
        "title_color": "#666",
        "status_color": "#888",
        "hint_color": "#aaa",
        "list_text": "#222",
        "list_hover": "rgba(230, 60, 60, 0.08)",
        "list_selected": "rgba(230, 60, 60, 0.15)",
        "btn_bg": "rgba(0, 0, 0, 0.05)",
        "btn_hover": "rgba(0, 0, 0, 0.1)",
        "btn_text": "#555",
    },
    "dark": {
        "bg": "rgba(30, 30, 40, 240)",
        "border": "rgba(255, 255, 255, 0.08)",
        "input_bg": "rgba(255, 255, 255, 0.06)",
        "input_border": "rgba(255, 255, 255, 0.15)",
        "input_focus_border": "rgba(255, 70, 70, 0.5)",
        "input_text": "#ffffff",
        "input_placeholder": "#777",
        "title_color": "#999",
        "status_color": "#777",
        "hint_color": "#555",
        "list_text": "#eee",
        "list_hover": "rgba(255, 70, 70, 0.15)",
        "list_selected": "rgba(255, 70, 70, 0.3)",
        "btn_bg": "rgba(255, 255, 255, 0.08)",
        "btn_hover": "rgba(255, 255, 255, 0.15)",
        "btn_text": "#bbb",
    },
}


class ArrowOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self._start = QPoint(0, 0)
        self._end = QPoint(0, 0)
        self._progress = 0.0
        self._opacity = 1.0
        self._visible = False

        self._anim = QPropertyAnimation(self, b"progress")
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_anim = QPropertyAnimation(self, b"opacity_val")
        self._fade_anim.setDuration(3000)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.InQuad)
        self._fade_anim.finished.connect(self._on_fade_done)

    def get_progress(self):
        return self._progress

    def set_progress(self, val):
        self._progress = val
        self.update()

    progress = pyqtProperty(float, get_progress, set_progress)

    def get_opacity_val(self):
        return self._opacity

    def set_opacity_val(self, val):
        self._opacity = val
        self.update()

    opacity_val = pyqtProperty(float, get_opacity_val, set_opacity_val)

    def show_arrow(self, start: QPoint, end: QPoint):
        self._start = start
        self._end = end
        self._progress = 0.0
        self._opacity = 1.0
        self._visible = True
        self.show()
        self.raise_()

        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

        self._fade_anim.stop()
        QTimer.singleShot(2500, self._start_fade)

    def _start_fade(self):
        self._fade_anim.start()

    def _on_fade_done(self):
        self._visible = False
        self.hide()

    def paintEvent(self, event):
        if not self._visible or self._progress <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        sx, sy = self._start.x(), self._start.y()
        ex, ey = self._end.x(), self._end.y()

        cx = sx + (ex - sx) * self._progress
        cy = sy + (ey - sy) * self._progress

        pen = QPen(QColor(230, 60, 60), 5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(sx), int(sy), int(cx), int(cy))

        if self._progress > 0.05:
            angle = math.atan2(ey - sy, ex - sx)
            arrow_size = 35

            p1x = cx - arrow_size * math.cos(angle - math.pi / 6)
            p1y = cy - arrow_size * math.sin(angle - math.pi / 6)
            p2x = cx - arrow_size * math.cos(angle + math.pi / 6)
            p2y = cy - arrow_size * math.sin(angle + math.pi / 6)

            arrow_head = QPolygonF([
                QRectF(cx - 1, cy - 1, 2, 2).center(),
                QRectF(p1x - 1, p1y - 1, 2, 2).center(),
                QRectF(p2x - 1, p2y - 1, 2, 2).center(),
            ])

            painter.setBrush(QBrush(QColor(230, 60, 60)))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(arrow_head)

        if self._progress >= 1.0:
            painter.setPen(QPen(QColor(230, 60, 60, 200), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPoint(int(ex), int(ey)), 30, 30)
            painter.setPen(QPen(QColor(230, 60, 60, 100), 2))
            painter.drawEllipse(QPoint(int(ex), int(ey)), 45, 45)

        painter.end()


class SearchWindow(QWidget):
    results_ready = pyqtSignal(list)
    explorer_found = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Finder")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(560, 500)

        self._drag_pos = None
        self._theme = "light"

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        self._all_results = []
        self._icon_positions = {}
        self._refresh_icons()

        self.results_ready.connect(self._on_results)
        self.explorer_found.connect(self._on_explorer_found)

        self._init_ui()
        self._apply_theme()
        self._center_on_screen()

        self.overlay = ArrowOverlay()

    def _refresh_icons(self):
        self._icon_positions = get_desktop_icon_positions()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.container = QWidget()
        self.container.setObjectName("container")

        inner = QVBoxLayout(self.container)
        inner.setContentsMargins(24, 18, 24, 18)
        inner.setSpacing(10)

        # header row: title + theme toggle
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Desktop Finder")
        self.title_label.setObjectName("title")
        header.addWidget(self.title_label)

        header.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header.addWidget(self.theme_btn)

        inner.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput")
        self.search_input.setPlaceholderText("搜索文件或文件夹...")
        self.search_input.textChanged.connect(self._on_text_changed)
        inner.addWidget(self.search_input)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignLeft)
        inner.addWidget(self.status_label)

        self.result_list = QListWidget()
        self.result_list.setObjectName("resultList")
        self.result_list.itemClicked.connect(self._on_item_clicked)
        self.result_list.itemActivated.connect(self._on_item_clicked)
        inner.addWidget(self.result_list)

        self.hint_label = QLabel("桌面文件指向图标 | 其他文件打开文件夹 | Esc退出")
        self.hint_label.setObjectName("hint")
        self.hint_label.setAlignment(Qt.AlignCenter)
        inner.addWidget(self.hint_label)

        layout.addWidget(self.container)

    def _apply_theme(self):
        t = THEMES[self._theme]
        self.theme_btn.setText("🌙" if self._theme == "light" else "☀️")

        self.container.setStyleSheet(f"""
            #container {{
                background-color: {t['bg']};
                border-radius: 16px;
                border: 1px solid {t['border']};
            }}
        """)

        self.title_label.setStyleSheet(f"""
            #title {{
                color: {t['title_color']};
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
        """)

        self.theme_btn.setStyleSheet(f"""
            #themeBtn {{
                background-color: {t['btn_bg']};
                border: none;
                border-radius: 16px;
                font-size: 14px;
            }}
            #themeBtn:hover {{
                background-color: {t['btn_hover']};
            }}
        """)

        self.search_input.setStyleSheet(f"""
            #searchInput {{
                background-color: {t['input_bg']};
                border: 1px solid {t['input_border']};
                border-radius: 12px;
                padding: 14px 18px;
                font-size: 15px;
                color: {t['input_text']};
            }}
            #searchInput:focus {{
                border: 1px solid {t['input_focus_border']};
            }}
        """)

        self.status_label.setStyleSheet(f"""
            #status {{
                color: {t['status_color']};
                font-size: 11px;
                padding-left: 4px;
            }}
        """)

        self.result_list.setStyleSheet(f"""
            #resultList {{
                background-color: transparent;
                border: none;
                color: {t['list_text']};
                font-size: 13px;
            }}
            #resultList::item {{
                padding: 8px 12px;
                border-radius: 6px;
            }}
            #resultList::item:hover {{
                background-color: {t['list_hover']};
            }}
            #resultList::item:selected {{
                background-color: {t['list_selected']};
            }}
        """)

        self.hint_label.setStyleSheet(f"""
            #hint {{
                color: {t['hint_color']};
                font-size: 11px;
            }}
        """)

    def _toggle_theme(self):
        self._theme = "dark" if self._theme == "light" else "light"
        self._apply_theme()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 3
        self.move(x, y)

    def _on_text_changed(self, text):
        self._search_timer.start()

    def _do_search(self):
        query = self.search_input.text().strip()
        if len(query) < 2:
            self.result_list.clear()
            self.status_label.setText("")
            return

        self.status_label.setText("搜索中...")
        search_files(query, self._on_search_done)

    def _on_search_done(self, paths):
        self.results_ready.emit(paths)

    def _on_results(self, paths):
        self.result_list.clear()
        self._all_results = paths

        if not paths:
            self.status_label.setText("没有找到匹配的文件")
            return

        self.status_label.setText(f"找到 {len(paths)} 个文件")

        for p in paths:
            filename = os.path.basename(p)
            folder = os.path.dirname(p)
            item = QListWidgetItem(f"{filename}\n  {folder}")
            item.setData(Qt.UserRole, p)
            item.setData(Qt.UserRole + 1, filename)
            self.result_list.addItem(item)

    def _is_on_desktop(self, filepath):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        public_desktop = "C:\\Users\\Public\\Desktop"
        parent = os.path.dirname(os.path.normpath(filepath))
        return parent.lower() in (desktop.lower(), public_desktop.lower())

    def _on_item_clicked(self, item):
        filepath = item.data(Qt.UserRole)
        filename = item.data(Qt.UserRole + 1)
        if not filepath:
            return

        if self._is_on_desktop(filepath):
            target_pos = self._find_icon_pos(filename)
            if target_pos:
                start = self.mapToGlobal(self.search_input.geometry().center())
                end = QPoint(target_pos[0], target_pos[1])
                self.overlay.show_arrow(start, end)
                return

        if os.path.exists(filepath):
            open_in_explorer(filepath)

            def find_explorer():
                import time
                time.sleep(1.0)
                rect = get_newest_explorer_rect(timeout=3.0)
                if rect:
                    self.explorer_found.emit(rect[0], rect[1])

            t = threading.Thread(target=find_explorer, daemon=True)
            t.start()

    def _find_icon_pos(self, filename):
        if filename in self._icon_positions:
            return self._icon_positions[filename]

        self._refresh_icons()
        if filename in self._icon_positions:
            return self._icon_positions[filename]

        name_no_ext = os.path.splitext(filename)[0]
        for key, pos in self._icon_positions.items():
            if key == name_no_ext or key.startswith(name_no_ext):
                return pos

        return None

    def _on_explorer_found(self, cx, cy):
        start = self.mapToGlobal(self.search_input.geometry().center())
        end = QPoint(cx, cy)
        self.overlay.show_arrow(start, end)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.quit()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            current = self.result_list.currentItem()
            if current:
                self._on_item_clicked(current)
            elif self.result_list.count() > 0:
                self.result_list.setCurrentRow(0)
                self._on_item_clicked(self.result_list.item(0))
        elif event.key() == Qt.Key_Down:
            row = self.result_list.currentRow()
            if row < self.result_list.count() - 1:
                self.result_list.setCurrentRow(row + 1)
        elif event.key() == Qt.Key_Up:
            row = self.result_list.currentRow()
            if row > 0:
                self.result_list.setCurrentRow(row - 1)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SearchWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
