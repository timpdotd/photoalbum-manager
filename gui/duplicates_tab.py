import os
import cv2
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QCheckBox, QComboBox, QScrollArea, QFrame,
    QProgressBar, QMessageBox, QGridLayout, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage
from gui.workers.compare_worker import CompareWorker
from gui.workers.save_worker import SaveWorker
from core.batch_actions import execute_save
from core.scanner import is_video_file
from PySide6.QtWidgets import QLayout
from PySide6.QtCore import QPoint, QRect, QSize, QThread

class ThumbnailWorker(QThread):
    thumbnail_ready = Signal(str, QImage)
    
    def __init__(self, paths, size):
        super().__init__()
        self.paths = paths
        self.size = size
        self._is_running = True

    def run(self):
        for path in self.paths:
            if not self._is_running:
                break
                
            img = None
            if is_video_file(path):
                try:
                    cap = cv2.VideoCapture(path)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame.shape
                        qimg = QImage(frame.data, w, h, ch * w, QImage.Format_RGB888)
                        img = qimg.scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                except Exception:
                    pass
            else:
                qimg = QImage(path)
                if not qimg.isNull():
                    img = qimg.scaled(self.size, self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
            if img and not img.isNull():
                self.thumbnail_ready.emit(path, img)

    def stop(self):
        self._is_running = False

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing
        self.itemList = []
        if margin != -1:
            self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def horizontalSpacing(self):
        if self.m_hSpace >= 0: return self.m_hSpace
        return 10

    def verticalSpacing(self):
        if self.m_vSpace >= 0: return self.m_vSpace
        return 10

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            spaceX = self.horizontalSpacing()
            spaceY = self.verticalSpacing()
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class CollapsibleBox(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QPushButton(f"▼  {title}")
        self.toggle_button.setStyleSheet("text-align: left; padding: 10px; font-weight: bold; background-color: #374151; color: white; border: none; border-top-left-radius: 8px; border-top-right-radius: 8px;")
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.clicked.connect(self.toggle)
        
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: #1f2937; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 15)
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_frame)
        
        self.is_collapsed = False
        
    def toggle(self):
        self.is_collapsed = not self.is_collapsed
        self.content_frame.setVisible(not self.is_collapsed)
        arrow = "▶" if self.is_collapsed else "▼"
        current_title = self.toggle_button.text().split("  ", 1)[1]
        self.toggle_button.setText(f"{arrow}  {current_title}")

    def addWidget(self, widget):
        self.content_layout.addWidget(widget)
        
    def addLayout(self, layout):
        self.content_layout.addLayout(layout)

class DuplicatesTab(QWidget):
    def __init__(self, workspace_path, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self.current_folder = workspace_path
        
        self.worker = None
        self.thumb_worker = None
        self.duplicate_groups_dict = {} # dict mapping folder path to groups
        self.delete_checkboxes = {} # dict mapping file path to its QCheckBox
        self.thumbnail_labels = {} # dict mapping file path to its ClickableLabel
        
        self.init_ui()

    def set_folder_path(self, folder):
        self.current_folder = folder
        self.lbl_current_folder.setText(f"Cartella Corrente: {folder}")
        self.clear_results()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # --- CONTROLLI IN ALTO (Collapsible) ---
        self.controls_box = CollapsibleBox("Pannello di Ricerca")
        
        self.lbl_current_folder = QLabel(f"Cartella Corrente: {self.current_folder}")
        self.lbl_current_folder.setStyleSheet("font-weight: bold; color: #9ca3af; margin-bottom: 10px;")
        self.controls_box.addWidget(self.lbl_current_folder)
        
        config_layout = QHBoxLayout()
        
        # Soglie Hash
        sliders_layout = QGridLayout()
        sliders_layout.addWidget(QLabel("Sensibilità di Ricerca (Tolleranza Hash):"), 0, 0)
        self.combo_hash = QComboBox()
        self.combo_hash.addItem("1 - Molto Basso (Tanti falsi positivi)", 0)
        self.combo_hash.addItem("2 - Basso", 25)
        self.combo_hash.addItem("3 - Medio", 50)
        self.combo_hash.addItem("4 - Alto", 75)
        self.combo_hash.addItem("5 - Molto Alto (Quasi identiche)", 100)
        self.combo_hash.setCurrentIndex(2) # Default 50 (Medio)
        sliders_layout.addWidget(self.combo_hash, 0, 1)
        
        config_layout.addLayout(sliders_layout)
        
        self.btn_start = QPushButton("🔍 Avvia Ricerca nelle Sottocartelle")
        self.btn_start.setStyleSheet("background-color: #6366f1; color: white; font-weight: bold; padding: 10px; margin-left: 20px; border-radius: 6px;")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_comparison)
        config_layout.addWidget(self.btn_start)
        
        self.controls_box.addLayout(config_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.controls_box.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.controls_box)

        # --- RISULTATI IN BASSO ---
        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Risultati Ricerca:"))
        header_layout.addStretch()
        self.btn_apply = QPushButton("💾 Applica Eliminazioni")
        self.btn_apply.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; padding: 8px 20px; border-radius: 6px;")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self.apply_deletions)
        self.btn_apply.setEnabled(False)
        header_layout.addWidget(self.btn_apply)
        results_layout.addLayout(header_layout)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 15, 0)
        self.scroll_area.setWidget(self.scroll_widget)
        
        results_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(results_frame)

    def start_comparison(self):
        self.clear_results()
        self.btn_start.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        self.worker = CompareWorker(
            target_folder=self.current_folder,
            root_path=self.workspace_path,
            hash_tol=self.combo_hash.currentData()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.work_finished.connect(self.on_comparison_finished)
        self.worker.error.connect(self.on_comparison_error)
        self.worker.start()

    def on_comparison_finished(self, groups_dict):
        self.progress_bar.hide()
        self.btn_start.setEnabled(True)
        self.duplicate_groups_dict = groups_dict
        
        # Collassa il pannello di ricerca per dare spazio ai risultati se ce ne sono
        if groups_dict and not self.controls_box.is_collapsed:
            self.controls_box.toggle()
            
        self.render_results()

    def on_comparison_error(self, err_msg):
        self.progress_bar.hide()
        self.btn_start.setEnabled(True)
        QMessageBox.critical(self, "Errore", f"Errore durante la comparazione: {err_msg}")

    def clear_results(self):
        if self.thumb_worker and self.thumb_worker.isRunning():
            self.thumb_worker.stop()
            self.thumb_worker.wait()
            
        self.duplicate_groups_dict = {}
        self.delete_checkboxes.clear()
        self.thumbnail_labels.clear()
        self.btn_apply.setEnabled(False)
        
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())

    def on_thumbnail_ready(self, path, qimage):
        if path in self.thumbnail_labels:
            lbl = self.thumbnail_labels[path]
            lbl.setPixmap(QPixmap.fromImage(qimage))
            
    def show_preview(self, path):
        try:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            success = QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            if not success:
                QMessageBox.warning(self, "Errore", "Impossibile trovare un'applicazione predefinita per aprire questo file.")
        except Exception as e:
            QMessageBox.warning(self, "Errore", f"Errore durante l'apertura:\n{e}")

    def render_results(self):
        if not self.duplicate_groups_dict:
            lbl = QLabel("Nessun duplicato trovato con i criteri correnti.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #9ca3af; font-size: 14px; margin-top: 20px;")
            self.scroll_layout.addWidget(lbl)
            return
            
        self.btn_apply.setEnabled(True)
        paths_to_load = []
            
        for folder_path, groups in self.duplicate_groups_dict.items():
            folder_name = os.path.basename(os.path.normpath(folder_path))
            if not folder_name:
                folder_name = folder_path
                
            folder_box = CollapsibleBox(f"Cartella: {folder_name} ({len(groups)} gruppi trovati)")
            
            for i, group in enumerate(groups):
                is_video = is_video_file(group[0])
                media_type = "Video" if is_video else "Foto"
                
                group_box = CollapsibleBox(f"Gruppo {i+1} ({len(group)} {media_type})")
                
                # Bottone Seleziona Tutte
                btn_select_all = QPushButton("☑ Seleziona Tutte / Deseleziona Tutte")
                btn_select_all.setStyleSheet("background-color: #374151; color: #d1d5db; padding: 5px; border-radius: 4px; font-weight: bold;")
                btn_select_all.setCursor(Qt.PointingHandCursor)
                group_box.addWidget(btn_select_all)
                
                thumbs_widget = QWidget()
                thumbs_layout = FlowLayout(thumbs_widget)
                
                group_checkboxes = []
                
                for path in group:
                    item_layout = QVBoxLayout()
                    
                    # Thumbnail cliccabile
                    lbl_thumb = ClickableLabel()
                    lbl_thumb.setText("Caricamento...")
                    lbl_thumb.setFixedSize(400, 400)
                    lbl_thumb.setAlignment(Qt.AlignCenter)
                    lbl_thumb.setStyleSheet("background-color: #1f2937; border-radius: 4px; border: 1px solid #4b5563; color: #9ca3af;")
                    lbl_thumb.setCursor(Qt.PointingHandCursor)
                    lbl_thumb.setToolTip("Clicca per ingrandire")
                    lbl_thumb.clicked.connect(lambda p=path: self.show_preview(p))
                    item_layout.addWidget(lbl_thumb)
                    
                    self.thumbnail_labels[path] = lbl_thumb
                    paths_to_load.append(path)
                    
                    # Nome file (troncato se lungo)
                    fname = os.path.basename(path)
                    lbl_name = QLabel(fname)
                    lbl_name.setFixedWidth(400)
                    lbl_name.setToolTip(path)
                    lbl_name.setStyleSheet("color: #d1d5db; font-size: 11px;")
                    lbl_name.setAlignment(Qt.AlignCenter)
                    item_layout.addWidget(lbl_name)
                    
                    # Checkbox elimina
                    chk = QCheckBox("Elimina")
                    chk.setStyleSheet("color: #ef4444; font-weight: bold;")
                    self.delete_checkboxes[path] = chk
                    group_checkboxes.append(chk)
                    
                    chk_layout = QHBoxLayout()
                    chk_layout.setAlignment(Qt.AlignCenter)
                    chk_layout.addWidget(chk)
                    item_layout.addLayout(chk_layout)
                    
                    chk.stateChanged.connect(lambda state, l=lbl_thumb: 
                        l.setStyleSheet("background-color: #1f2937; border-radius: 4px; border: 3px solid #ef4444; color: #9ca3af;") 
                        if state else 
                        l.setStyleSheet("background-color: #1f2937; border-radius: 4px; border: 1px solid #4b5563; color: #9ca3af;")
                    )
                    
                    # Wrapper del singolo item per poterlo aggiungere al FlowLayout
                    single_item_widget = QWidget()
                    single_item_widget.setLayout(item_layout)
                    thumbs_layout.addWidget(single_item_widget)
                    
                # Collega il pulsante Seleziona Tutte
                btn_select_all.clicked.connect(lambda _, chks=group_checkboxes: self.toggle_group_checkboxes(chks))
                    
                group_box.addWidget(thumbs_widget)
                folder_box.addWidget(group_box)
                
            self.scroll_layout.addWidget(folder_box)
            
        if paths_to_load:
            self.thumb_worker = ThumbnailWorker(paths_to_load, 400)
            self.thumb_worker.thumbnail_ready.connect(self.on_thumbnail_ready)
            self.thumb_worker.start()

    def toggle_group_checkboxes(self, checkboxes):
        all_checked = all(c.isChecked() for c in checkboxes)
        for c in checkboxes:
            c.setChecked(not all_checked)

    def apply_deletions(self):
        pending_actions = {}
        count = 0
        for path, chk in self.delete_checkboxes.items():
            if chk.isChecked():
                pending_actions[path] = {"deleted": True, "rotation": 0, "printed": False}
                count += 1
                
        if count == 0:
            QMessageBox.information(self, "Info", "Nessun file selezionato per l'eliminazione.")
            return
            
        reply = QMessageBox.question(
            self, "Conferma Eliminazione", 
            f"Sei sicuro di voler eliminare {count} file?\nQuesta operazione non può essere annullata.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from PySide6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            self.btn_apply.setEnabled(False)
            
            self.save_worker = SaveWorker(pending_actions)
            self.save_worker.work_finished.connect(lambda: self.on_save_finished(count))
            self.save_worker.error.connect(self.on_save_error)
            self.save_worker.start()

    def on_save_finished(self, count):
        from PySide6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        self.btn_apply.setEnabled(True)
        QMessageBox.information(self, "Fatto", f"{count} file eliminati con successo.")
        # Ricarica
        self.start_comparison()
        
    def on_save_error(self, err_msg):
        from PySide6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        self.btn_apply.setEnabled(True)
        QMessageBox.critical(self, "Errore", f"Errore durante l'eliminazione: {err_msg}")
