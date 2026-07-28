import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QTreeView, 
    QFileSystemModel, QLabel, QLineEdit, QPushButton, QScrollArea, 
    QFrame, QFileDialog, QSizePolicy, QHeaderView, QStackedWidget
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt, QDir, QEvent, QUrl, QThread, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QTransform
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from core.batch_actions import execute_save
from core.scanner import SUPPORTED_EXTENSIONS, is_video_file
from gui.workers.save_worker import SaveWorker

class MoveWorker(QThread):
    work_finished = Signal(int)
    error = Signal(str)
    
    def __init__(self, file_paths, dest_folder):
        super().__init__()
        self.file_paths = file_paths
        self.dest_folder = dest_folder
        
    def run(self):
        try:
            from core.batch_actions import move_media_files
            count = move_media_files(self.file_paths, self.dest_folder)
            self.work_finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

class CheckableFileSystemModel(QFileSystemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked_paths = set()

    def flags(self, index):
        default_flags = super().flags(index)
        if index.isValid() and index.column() == 0:
            return default_flags | Qt.ItemIsUserCheckable
        return default_flags

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
            return Qt.Checked if path in self.checked_paths else Qt.Unchecked
        return super().data(index, role)

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            path = self.filePath(index)
            if value == Qt.Checked or value == 2:
                self.checked_paths.add(path)
            else:
                self.checked_paths.discard(path)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return super().setData(index, value, role)
        
    def get_checked_paths(self):
        # Filtra solo i path che esistono ancora (in caso di eliminazioni)
        import os
        valid = {p for p in self.checked_paths if os.path.exists(p)}
        self.checked_paths = valid
        return list(valid)
        
    def clear_checked(self):
        self.checked_paths.clear()
        self.layoutChanged.emit()

class ViewerTab(QWidget):
    def __init__(self, default_path, parent=None):
        super().__init__(parent)
        self.current_folder_path = default_path
        self.current_image_path = None
        self.original_pixmap = None
        self.zoom_factor = 1.0
        self.auto_fit = True
        
        # Stato del drag-to-pan
        self.pan_active = False
        self.pan_start_pos = None
        
        self.pending_actions = {}

        
        self.init_ui()

    def init_ui(self):
        # Layout principale orizzontale
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Usiamo un QSplitter per consentire il ridimensionamento flessibile dei pannelli
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: rgba(255, 255, 255, 0.08); }")

        # --- PANNELLO SINISTRO: SIDEBAR (File Tree Explorer) ---
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("sidebarPanel")
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        
        sidebar_title = QLabel("Esploratore File")
        sidebar_title.setObjectName("sectionTitle")
        sidebar_layout.addWidget(sidebar_title)

        # Configurazione Albero File System (con supporto Checkboxes)
        self.file_model = CheckableFileSystemModel()
        self.file_model.setRootPath(self.current_folder_path)
        
        # Filtriamo per mostrare solo cartelle e file supportati
        self.file_model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        name_filters = [f"*{ext}" for ext in SUPPORTED_EXTENSIONS]
        self.file_model.setNameFilters(name_filters)
        self.file_model.setNameFilterDisables(False) # Nasconde i file non corrispondenti invece di disabilitarli
        self.file_model.setReadOnly(False) # Abilita rinomina e modifica

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(self.current_folder_path))
        self.tree_view.clicked.connect(self.on_tree_item_clicked)
        # Permette di cambiare foto muovendosi con le frecce Su/Giù native dell'albero
        self.tree_view.selectionModel().currentChanged.connect(self.on_tree_current_changed)
        
        # Abilita Drag and Drop e Multiselezione
        self.tree_view.setSelectionMode(QTreeView.ExtendedSelection)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setAcceptDrops(True)
        self.tree_view.setDropIndicatorShown(True)
        self.tree_view.setDragDropMode(QTreeView.InternalMove)
        
        # Context Menu
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Nascondiamo le colonne non necessarie (dimensione, tipo, data modifica) nell'albero
        self.tree_view.setHeaderHidden(True)
        for i in range(1, self.file_model.columnCount()):
            self.tree_view.setColumnHidden(i, True)
            
        # Forza la colonna ad adattarsi al contenuto e abilita lo scroll orizzontale
        self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_view.header().setStretchLastSection(False)

        sidebar_layout.addWidget(self.tree_view)

        # Pulsanti di azione rapidi sotto l'albero
        tree_buttons_layout = QHBoxLayout()
        tree_buttons_layout.setSpacing(8)
        
        self.btn_sidebar_new_folder = QPushButton("📁 Nuova Cartella")
        self.btn_sidebar_new_folder.setObjectName("btnRefresh") # Stile secondario
        self.btn_sidebar_new_folder.setCursor(Qt.PointingHandCursor)
        self.btn_sidebar_new_folder.clicked.connect(self.sidebar_new_folder)
        tree_buttons_layout.addWidget(self.btn_sidebar_new_folder)
        
        self.btn_sidebar_move = QPushButton("📦 Sposta Selezionati")
        self.btn_sidebar_move.setObjectName("btnRefresh") # Stile secondario
        self.btn_sidebar_move.setCursor(Qt.PointingHandCursor)
        self.btn_sidebar_move.clicked.connect(self.sidebar_move_selected)
        tree_buttons_layout.addWidget(self.btn_sidebar_move)
        
        sidebar_layout.addLayout(tree_buttons_layout)

        splitter.addWidget(sidebar_frame)

        # --- PANNELLO CENTRALE: VISUALIZZATORE FOTO/VIDEO ---
        viewer_frame = QFrame()
        viewer_frame.setObjectName("viewerPanel")
        viewer_layout = QVBoxLayout(viewer_frame)
        viewer_layout.setContentsMargins(12, 12, 12, 12)
        viewer_layout.setSpacing(10)

        # Intestazione e Controlli Zoom
        header_viewer_layout = QHBoxLayout()
        
        viewer_title = QLabel("Anteprima")
        viewer_title.setObjectName("sectionTitle")
        viewer_title.setStyleSheet("margin-bottom: 0px; border-bottom: none; padding-bottom: 0px;")
        header_viewer_layout.addWidget(viewer_title)
        
        header_viewer_layout.addStretch()

        # Controlli Zoom layout
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(6)

        self.lbl_zoom_level = QLabel("Zoom: -")
        self.lbl_zoom_level.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: bold; margin-right: 10px;")
        zoom_layout.addWidget(self.lbl_zoom_level)

        self.btn_zoom_in = QPushButton("➕ In")
        self.btn_zoom_in.setObjectName("btnRefresh")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        zoom_layout.addWidget(self.btn_zoom_in)

        self.btn_zoom_out = QPushButton("➖ Out")
        self.btn_zoom_out.setObjectName("btnRefresh")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        zoom_layout.addWidget(self.btn_zoom_out)

        self.btn_zoom_reset = QPushButton("🔄 100%")
        self.btn_zoom_reset.setObjectName("btnRefresh")
        self.btn_zoom_reset.clicked.connect(self.zoom_reset)
        zoom_layout.addWidget(self.btn_zoom_reset)

        self.btn_zoom_fit = QPushButton("📺 Adatta")
        self.btn_zoom_fit.setObjectName("btnRefresh")
        self.btn_zoom_fit.clicked.connect(self.zoom_fit)
        zoom_layout.addWidget(self.btn_zoom_fit)

        header_viewer_layout.addLayout(zoom_layout)
        viewer_layout.addLayout(header_viewer_layout)

        # Toolbar Azioni
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        self.btn_action_delete = QPushButton("🗑️ Elimina")
        self.btn_action_delete.clicked.connect(self.action_delete)
        actions_layout.addWidget(self.btn_action_delete)
        
        self.btn_action_rot_l = QPushButton("↩️ Ruota Sx")
        self.btn_action_rot_l.clicked.connect(self.action_rotate_left)
        actions_layout.addWidget(self.btn_action_rot_l)
        
        self.btn_action_rot_r = QPushButton("↪️ Ruota Dx")
        self.btn_action_rot_r.clicked.connect(self.action_rotate_right)
        actions_layout.addWidget(self.btn_action_rot_r)
        
        self.btn_action_print = QPushButton("🖨️ Segna Stampata")
        self.btn_action_print.clicked.connect(self.action_mark_printed)
        actions_layout.addWidget(self.btn_action_print)
        
        self.btn_action_move = QPushButton("📦 Sposta in...")
        self.btn_action_move.clicked.connect(self.action_move_current)
        actions_layout.addWidget(self.btn_action_move)
        
        self.btn_action_play = QPushButton("▶️ Play/Pausa")
        self.btn_action_play.clicked.connect(self.action_toggle_playback)
        self.btn_action_play.hide()
        actions_layout.addWidget(self.btn_action_play)
        
        actions_layout.addStretch()
        
        self.btn_save_changes = QPushButton("💾 Salva Modifiche")
        self.btn_save_changes.setStyleSheet("background-color: #10b981; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_save_changes.clicked.connect(self.save_changes)
        self.btn_save_changes.setEnabled(False)
        actions_layout.addWidget(self.btn_save_changes)
        
        self.btn_cancel_changes = QPushButton("❌ Annulla")
        self.btn_cancel_changes.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; padding: 5px 10px;")
        self.btn_cancel_changes.clicked.connect(self.cancel_changes)
        self.btn_cancel_changes.setEnabled(False)
        actions_layout.addWidget(self.btn_cancel_changes)
        
        viewer_layout.addLayout(actions_layout)

        # Linea divisoria per allineamento estetico
        div_line = QFrame()
        div_line.setFrameShape(QFrame.HLine)
        div_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); max-height: 1px; border: none;")
        viewer_layout.addWidget(div_line)

        # Stacked widget to switch between Image and Video
        self.viewer_stack = QStackedWidget()

        # Area di scorrimento per ospitare l'immagine
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidgetResizable(True)

        # Label per contenere l'immagine
        self.image_label = QLabel("Seleziona un file dall'elenco a sinistra per visualizzarlo")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #6b7280; font-size: 14px;")
        self.image_label.setWordWrap(True)
        self.scroll_area.setWidget(self.image_label)
        
        self.viewer_stack.addWidget(self.scroll_area)
        
        # Setup Video Player
        self.video_widget = QVideoWidget()
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        self.viewer_stack.addWidget(self.video_widget)

        viewer_layout.addWidget(self.viewer_stack)
        splitter.addWidget(viewer_frame)

        # Impostiamo le proporzioni iniziali dello splitter (sidebar, viewer)
        # Più spazio all'albero (es. 400px) e il resto al visualizzatore
        splitter.setSizes([400, 750])
        main_layout.addWidget(splitter)

        # --- SCORCIATOIE DA TASTIERA GLOBALI (QShortcut) ---
        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self.action_delete)
        QShortcut(QKeySequence(Qt.Key_Backspace), self).activated.connect(self.action_delete)
        QShortcut(QKeySequence(Qt.Key_P), self).activated.connect(self.action_mark_printed)
        
        # Le frecce destra/sinistra ruotano la foto
        QShortcut(QKeySequence(Qt.Key_Left), self).activated.connect(self.action_rotate_left)
        QShortcut(QKeySequence(Qt.Key_Right), self).activated.connect(self.action_rotate_right)
        
        # Frecce Su/Giù per navigare l'albero forzatamente se il focus non è sull'albero
        QShortcut(QKeySequence(Qt.Key_Up), self).activated.connect(lambda: self.navigate_tree(-1))
        QShortcut(QKeySequence(Qt.Key_Down), self).activated.connect(lambda: self.navigate_tree(1))

        # --- FILTRI EVENTI PER ROTAZIONE ROTELLINA E TRASCINAMENTO ---
        self.scroll_area.viewport().installEventFilter(self)
        self.image_label.installEventFilter(self)

    def set_folder_path(self, folder):
        self.current_folder_path = folder
        self.file_model.setRootPath(folder)
        self.tree_view.setRootIndex(self.file_model.index(folder))
        self.pending_actions.clear()
        self.check_pending_changes()
        self.clear_viewer()

    def refresh_tree(self):
        # Ripristina la visualizzazione dell'albero per la cartella corrente
        self.file_model.setRootPath(self.current_folder_path)
        self.tree_view.setRootIndex(self.file_model.index(self.current_folder_path))

    def show_context_menu(self, position):
        from PySide6.QtWidgets import QMenu, QInputDialog, QMessageBox, QFileDialog
        from core.batch_actions import move_media_files
        import shutil
        
        # 1. Recupera gli elementi selezionati nella TreeView
        selected_rows = self.tree_view.selectionModel().selectedRows()
        selected_paths = [self.file_model.filePath(idx) for idx in selected_rows]
        selected_paths = [p for p in selected_paths if os.path.exists(p)]
        
        # Se non c'è selezione tasto destro su un elemento specifico, proviamo ad ottenere l'indice cliccato
        index = self.tree_view.indexAt(position)
        file_path = self.file_model.filePath(index) if index.isValid() else self.current_folder_path
        is_dir = self.file_model.isDir(index) if index.isValid() else True
        
        menu = QMenu()
        
        checked_files = self.file_model.get_checked_paths()
        
        action_move_selected_to = None
        action_move_checked_to = None
        action_move_checked_here = None
        
        # Opzioni di spostamento per elementi selezionati
        if selected_paths:
            action_move_selected_to = menu.addAction(f"📦 Sposta i {len(selected_paths)} elementi selezionati altrove...")
            
        # Opzioni di spostamento per elementi spuntati
        if checked_files:
            action_move_checked_to = menu.addAction(f"📦 Sposta i {len(checked_files)} file spuntati altrove...")
            action_move_checked_here = menu.addAction(f"📦 Sposta i {len(checked_files)} file spuntati qui...")
            
        if selected_paths or checked_files:
            menu.addSeparator()
            
        action_new_folder = menu.addAction("📁 Nuova Cartella...")
        action_rename = menu.addAction("✏️ Rinomina")
        action_delete = menu.addAction("🗑️ Elimina Fisicamente")
        
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))
        if not action:
            return
            
        target_dir = file_path if is_dir else os.path.dirname(file_path)
        
        # Esecuzione azioni
        if action == action_move_selected_to:
            dest_dir = QFileDialog.getExistingDirectory(self, "Seleziona cartella di destinazione", target_dir)
            if dest_dir:
                from PySide6.QtWidgets import QApplication
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    moved = move_media_files(selected_paths, dest_dir)
                    QMessageBox.information(self, "Spostamento Completato", f"{moved} elementi spostati con successo in:\n{dest_dir}")
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento: {e}")
                finally:
                    QApplication.restoreOverrideCursor()
                self.refresh_tree()
                
        elif action == action_move_checked_to:
            dest_dir = QFileDialog.getExistingDirectory(self, "Seleziona cartella di destinazione", target_dir)
            if dest_dir:
                from PySide6.QtWidgets import QApplication
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    moved = move_media_files(checked_files, dest_dir)
                    self.file_model.clear_checked()
                    QMessageBox.information(self, "Spostamento Completato", f"{moved} file spuntati spostati con successo in:\n{dest_dir}")
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento: {e}")
                finally:
                    QApplication.restoreOverrideCursor()
                self.refresh_tree()
                
        elif action == action_move_checked_here:
            name, ok = QInputDialog.getText(self, "Sposta File Spuntati", "Nome della nuova cartella in cui spostarli:")
            if ok and name:
                new_path = os.path.join(target_dir, name)
                from PySide6.QtWidgets import QApplication
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    moved = move_media_files(checked_files, new_path)
                    self.file_model.clear_checked()
                    QMessageBox.information(self, "Spostamento Completato", f"{moved} file spuntati spostati con successo in:\n{new_path}")
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento: {e}")
                finally:
                    QApplication.restoreOverrideCursor()
                self.refresh_tree()
                
        elif action == action_new_folder:
            name, ok = QInputDialog.getText(self, "Nuova Cartella", "Nome della cartella da creare:")
            if ok and name:
                new_path = os.path.join(target_dir, name)
                try:
                    os.makedirs(new_path, exist_ok=True)
                    # Inizializza il file CSV nella nuova cartella
                    from core.batch_actions import update_csv
                    update_csv(new_path)
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Impossibile creare la cartella: {e}")
                self.refresh_tree()
                
        elif action == action_rename and index.isValid():
            self.tree_view.edit(index)
            
        elif action == action_delete and index.isValid():
            resp = QMessageBox.question(self, "Conferma Eliminazione", 
                                       f"Vuoi davvero eliminare fisicamente dal disco questo elemento?\n{os.path.basename(file_path)}\n\nATTENZIONE: L'azione è irreversibile!",
                                       QMessageBox.Yes | QMessageBox.No)
            if resp == QMessageBox.Yes:
                try:
                    if is_dir:
                        shutil.rmtree(file_path, ignore_errors=True)
                    else:
                        os.remove(file_path)
                        # Pulisce la riga dal CSV di provenienza
                        from core.batch_actions import update_csv
                        update_csv(target_dir, {os.path.basename(file_path): {"deleted": True}})
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Impossibile eliminare: {e}")
                self.refresh_tree()
                self.clear_viewer()

    def on_tree_current_changed(self, current, previous):
        if current.isValid():
            self.on_tree_item_clicked(current)

    def on_tree_item_clicked(self, index):
        path = self.file_model.filePath(index)
        if not self.file_model.isDir(index):
            # Controlla se è un'estensione supportata
            _, ext = os.path.splitext(path.lower())
            if ext in SUPPORTED_EXTENSIONS:
                self.load_image(path)

    def load_image(self, path):
        self.current_image_path = path
        
        if is_video_file(path):
            actions = self.pending_actions.get(path, {})
            is_deleted = actions.get("deleted", False)
            
            self.btn_action_play.show()
            self.btn_action_rot_l.setEnabled(False)
            self.btn_action_rot_r.setEnabled(False)
            self.btn_action_print.setEnabled(False) # Disabilita stampa per i video
            self.btn_zoom_in.setEnabled(False)
            self.btn_zoom_out.setEnabled(False)
            self.btn_zoom_fit.setEnabled(False)
            self.btn_zoom_reset.setEnabled(False)
            self.lbl_zoom_level.setText("Video")
            
            if is_deleted:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
                self.show_video_overlay_message("🗑️ VIDEO SEGNATO PER L'ELIMINAZIONE")
            else:
                self.viewer_stack.setCurrentIndex(1)
                self.media_player.setSource(QUrl.fromLocalFile(path))
                self.media_player.play()
            return
            
        self.viewer_stack.setCurrentIndex(0)
        self.btn_action_play.hide()
        self.btn_action_rot_l.setEnabled(True)
        self.btn_action_rot_r.setEnabled(True)
        self.btn_action_print.setEnabled(True) # Abilita stampa per le foto
        self.btn_zoom_in.setEnabled(True)
        self.btn_zoom_out.setEnabled(True)
        self.btn_zoom_fit.setEnabled(True)
        self.btn_zoom_reset.setEnabled(True)
        self.media_player.stop()
        self.media_player.setSource(QUrl())

        pixmap = QPixmap(path)
        
        if pixmap.isNull():
            self.image_label.setText("Errore nel caricamento dell'immagine.")
            return

        self.original_pixmap = pixmap
        # Applica la visualizzazione (mantiene auto_fit corrente)
        self.update_image_display()

    def update_image_display(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return

        # Use absolute path for pending actions
        file_path = self.current_image_path
        actions = self.pending_actions.get(file_path, {})
        rotation = actions.get("rotation", 0) % 360
        deleted = actions.get("deleted", False)
        printed = actions.get("printed", False)

        # Apply rotation to original
        display_pixmap = self.original_pixmap
        if rotation != 0:
            transform = QTransform().rotate(rotation)
            display_pixmap = display_pixmap.transformed(transform, Qt.SmoothTransformation)

        # Sottraiamo un piccolo offset per evitare scrollbar non necessarie in modalità fit
        w_viewport = self.scroll_area.viewport().width() - 10
        h_viewport = self.scroll_area.viewport().height() - 10
        if w_viewport <= 0 or h_viewport <= 0:
            return

        if self.auto_fit:
            self.scroll_area.setWidgetResizable(False)
            scaled_pixmap = display_pixmap.scaled(
                w_viewport, h_viewport, 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            # Calcola percentuale zoom effettiva
            pct = int((scaled_pixmap.width() / display_pixmap.width()) * 100)
            self.lbl_zoom_level.setText(f"Zoom: {pct}% (Adatto)")
        else:
            self.scroll_area.setWidgetResizable(False)
            w = int(display_pixmap.width() * self.zoom_factor)
            h = int(display_pixmap.height() * self.zoom_factor)
            if w <= 0 or h <= 0:
                return
            scaled_pixmap = display_pixmap.scaled(
                w, h, 
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            self.lbl_zoom_level.setText(f"Zoom: {int(self.zoom_factor * 100)}%")

        # Draw Overlays (Elegant badges)
        final_pixmap = scaled_pixmap.copy()
        if deleted or printed:
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Badge Eliminata (Top-Left)
            if deleted:
                # Disegna bordo rosso
                pen = QPen(QColor(239, 68, 68, 200)) # Tailwind red-500
                pen.setWidth(6)
                painter.setPen(pen)
                painter.drawRect(final_pixmap.rect())
                
                # Sfondo etichetta
                painter.setBrush(QColor(239, 68, 68, 230))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(10, 10, 140, 34, 6, 6)
                
                # Testo etichetta
                painter.setPen(Qt.white)
                font = QFont("Arial", 12, QFont.Bold)
                painter.setFont(font)
                painter.drawText(10, 10, 140, 34, Qt.AlignCenter, "🗑️ ELIMINATA")
                
            # Badge Stampata (Top-Right)
            if printed and not deleted:
                # Disegna bordo verde
                pen = QPen(QColor(16, 185, 129, 200)) # Tailwind emerald-500
                pen.setWidth(6)
                painter.setPen(pen)
                painter.drawRect(final_pixmap.rect())
                
                # Sfondo etichetta
                w = final_pixmap.width()
                painter.setBrush(QColor(16, 185, 129, 230))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(w - 150, 10, 140, 34, 6, 6)
                
                # Testo etichetta
                painter.setPen(Qt.white)
                font = QFont("Arial", 12, QFont.Bold)
                painter.setFont(font)
                painter.drawText(w - 150, 10, 140, 34, Qt.AlignCenter, "🖨️ STAMPATA")
                
            painter.end()

        self.image_label.setPixmap(final_pixmap)
        self.image_label.setFixedSize(final_pixmap.size())

    def zoom_in(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        
        if self.auto_fit:
            # Calcola lo zoom factor corrente prima di disattivare l'auto-fit
            self.zoom_factor = self.image_label.pixmap().width() / self.original_pixmap.width()
            self.auto_fit = False
            
        self.zoom_factor *= 1.15
        if self.zoom_factor > 10.0:
            self.zoom_factor = 10.0
            
        self.update_image_display()

    def zoom_out(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
            
        if self.auto_fit:
            # Calcola lo zoom factor corrente prima di disattivare l'auto-fit
            self.zoom_factor = self.image_label.pixmap().width() / self.original_pixmap.width()
            self.auto_fit = False
            
        self.zoom_factor /= 1.15
        if self.zoom_factor < 0.05:
            self.zoom_factor = 0.05
            
        self.update_image_display()

    def zoom_reset(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
            
        self.auto_fit = False
        self.zoom_factor = 1.0
        self.update_image_display()

    def zoom_fit(self):
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
            
        self.auto_fit = True
        self.update_image_display()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Ricalcola la scala dell'immagine al ridimensionamento (solo se in modalità fit)
        if self.original_pixmap and not self.original_pixmap.isNull() and self.auto_fit:
            self.update_image_display()

    def clear_viewer(self):
        self.current_image_path = None
        self.original_pixmap = None
        self.image_label.clear()
        self.scroll_area.setWidgetResizable(True)
        self.image_label.setText("Seleziona un file dall'elenco a sinistra per visualizzarlo")
        self.lbl_zoom_level.setText("Zoom: -")
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.viewer_stack.setCurrentIndex(0)

    def get_current_filepath(self):
        return self.current_image_path

    def init_action_state(self, filepath):
        if filepath not in self.pending_actions:
            self.pending_actions[filepath] = {"deleted": False, "rotation": 0, "printed": False}

    def check_pending_changes(self):
        has_changes = len(self.pending_actions) > 0
        self.btn_save_changes.setEnabled(has_changes)
        self.btn_cancel_changes.setEnabled(has_changes)

    def show_video_overlay_message(self, message, is_printed_only=False):
        self.viewer_stack.setCurrentIndex(0)
        
        # Crea una pixmap scura che si adatta all'area di visualizzazione
        w = max(self.scroll_area.viewport().width() - 10, 400)
        h = max(self.scroll_area.viewport().height() - 10, 300)
        
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor("#111827")) # Colore scuro premium
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Sfondo per il badge
        badge_width = 320
        badge_height = 50
        x = (w - badge_width) // 2
        y = (h - badge_height) // 2
        
        if is_printed_only:
            # Bordo verde
            pen = QPen(QColor(16, 185, 129, 200))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawRect(pixmap.rect())
            
            painter.setBrush(QColor(16, 185, 129, 230)) # Verde
        else:
            # Bordo rosso
            pen = QPen(QColor(239, 68, 68, 200))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawRect(pixmap.rect())
            
            painter.setBrush(QColor(239, 68, 68, 230)) # Rosso
            
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, badge_width, badge_height, 8, 8)
        
        # Testo
        painter.setPen(Qt.white)
        font = QFont("Arial", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(x, y, badge_width, badge_height, Qt.AlignCenter, message)
        
        # Aggiungi un testo di aiuto sotto
        painter.setPen(QColor("#9ca3af"))
        font_sub = QFont("Arial", 9)
        painter.setFont(font_sub)
        painter.drawText(0, y + badge_height + 15, w, 20, Qt.AlignCenter, "Premi nuovamente il pulsante per annullare l'azione")
        
        painter.end()
        
        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())

    def action_delete(self):
        filepath = self.get_current_filepath()
        if not filepath: return
        self.init_action_state(filepath)
        self.pending_actions[filepath]["deleted"] = not self.pending_actions[filepath]["deleted"]
        self.check_pending_changes()
        if is_video_file(filepath):
            if self.pending_actions[filepath]["deleted"]:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
                self.show_video_overlay_message("🗑️ VIDEO SEGNATO PER L'ELIMINAZIONE")
            else:
                # Ripristina riproduzione
                self.viewer_stack.setCurrentIndex(1)
                self.media_player.setSource(QUrl.fromLocalFile(filepath))
                self.media_player.play()
        else:
            self.update_image_display()

    def action_rotate_left(self):
        filepath = self.get_current_filepath()
        if not filepath: return
        self.init_action_state(filepath)
        self.pending_actions[filepath]["rotation"] -= 90
        self.check_pending_changes()
        self.update_image_display()

    def action_rotate_right(self):
        filepath = self.get_current_filepath()
        if not filepath: return
        self.init_action_state(filepath)
        self.pending_actions[filepath]["rotation"] += 90
        self.check_pending_changes()
        self.update_image_display()

    def action_mark_printed(self):
        filepath = self.get_current_filepath()
        if not filepath or is_video_file(filepath): return
        self.init_action_state(filepath)
        self.pending_actions[filepath]["printed"] = not self.pending_actions[filepath]["printed"]
        self.check_pending_changes()
        self.update_image_display()
            
    def action_toggle_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def save_changes(self):
        if not self.pending_actions: return
        
        # Libera i lock sui file multimediali svuotando l'anteprima
        self.clear_viewer()
        
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.btn_save_changes.setEnabled(False)
        self.btn_cancel_changes.setEnabled(False)
        
        self.save_worker = SaveWorker(self.pending_actions.copy())
        self.save_worker.work_finished.connect(self.on_save_finished)
        self.save_worker.error.connect(self.on_save_error)
        self.save_worker.start()

    def on_save_finished(self):
        from PySide6.QtWidgets import QApplication
        QApplication.restoreOverrideCursor()
        self.pending_actions.clear()
        self.check_pending_changes()
        self.refresh_tree()
        if self.current_image_path and os.path.exists(self.current_image_path):
            self.load_image(self.current_image_path)
        else:
            self.clear_viewer()
            
    def on_save_error(self, err_msg):
        from PySide6.QtWidgets import QApplication, QMessageBox
        QApplication.restoreOverrideCursor()
        self.check_pending_changes()
        QMessageBox.critical(self, "Errore", f"Errore durante il salvataggio: {err_msg}")

    def cancel_changes(self):
        self.pending_actions.clear()
        self.check_pending_changes()
        if self.current_image_path:
            self.load_image(self.current_image_path)

    @staticmethod
    def format_bytes(bytes_size):
        if bytes_size == 0:
            return "0 Bytes"
        k = 1024
        sizes = ["Bytes", "KB", "MB", "GB"]
        i = 0
        while bytes_size >= k and i < len(sizes) - 1:
            bytes_size /= k
            i += 1
        return f"{bytes_size:.2f} {sizes[i]}"

    def eventFilter(self, source, event):
        # 1. GESTIONE ROTELLINA DEL MOUSE (Wheel Zoom)
        if event.type() == QEvent.Wheel:
            if self.original_pixmap and not self.original_pixmap.isNull():
                angle_delta = event.angleDelta().y()
                if angle_delta > 0:
                    self.zoom_in()
                elif angle_delta < 0:
                    self.zoom_out()
                return True  # Blocca lo scrolling verticale di default

        # 2. GESTIONE TRASCINAMENTO (Drag-to-Pan) IN MODALITA' ZOOM
        if not self.auto_fit and self.original_pixmap and not self.original_pixmap.isNull():
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.pan_active = True
                    self.pan_start_pos = event.globalPosition().toPoint()
                    self.scroll_area.viewport().setCursor(Qt.ClosedHandCursor)
                    self.image_label.setCursor(Qt.ClosedHandCursor)
                    return True
            elif event.type() == QEvent.MouseMove:
                if self.pan_active and self.pan_start_pos is not None:
                    current_pos = event.globalPosition().toPoint()
                    delta = current_pos - self.pan_start_pos
                    self.pan_start_pos = current_pos
                    
                    h_bar = self.scroll_area.horizontalScrollBar()
                    v_bar = self.scroll_area.verticalScrollBar()
                    h_bar.setValue(h_bar.value() - delta.x())
                    v_bar.setValue(v_bar.value() - delta.y())
                    return True
            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.pan_active = False
                    self.scroll_area.viewport().setCursor(Qt.ArrowCursor)
                    self.image_label.setCursor(Qt.ArrowCursor)
                    return True
                    
        return super().eventFilter(source, event)

    def navigate_tree(self, direction):
        # Usato dalle scorciatoie globali Su/Giù se l'albero non ha il focus
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return
            
        if direction == -1:
            new_index = self.tree_view.indexAbove(current_index)
        else:
            new_index = self.tree_view.indexBelow(current_index)
            
        if new_index.isValid():
            # Impostando la corrente, scatterà on_tree_current_changed automaticamente
            self.tree_view.scrollTo(new_index)
            self.tree_view.setCurrentIndex(new_index)

    def sidebar_new_folder(self):
        from PySide6.QtWidgets import QInputDialog, QMessageBox
        # Trova la cartella selezionata correntemente
        indexes = self.tree_view.selectedIndexes()
        if indexes:
            index = indexes[0]
            file_path = self.file_model.filePath(index)
            is_dir = self.file_model.isDir(index)
            target_dir = file_path if is_dir else os.path.dirname(file_path)
        else:
            target_dir = self.current_folder_path
            
        name, ok = QInputDialog.getText(self, "Nuova Cartella", "Nome della cartella da creare:")
        if ok and name:
            new_path = os.path.join(target_dir, name)
            try:
                os.makedirs(new_path, exist_ok=True)
                from core.batch_actions import update_csv
                update_csv(new_path)
                self.refresh_tree()
            except Exception as e:
                QMessageBox.warning(self, "Errore", f"Impossibile creare la cartella: {e}")

    def sidebar_move_selected(self):
        from PySide6.QtWidgets import QMessageBox, QFileDialog, QApplication
        # 1. Ottieni file spuntati o selezionati
        checked_files = self.file_model.get_checked_paths()
        
        selected_rows = self.tree_view.selectionModel().selectedRows()
        selected_paths = [self.file_model.filePath(idx) for idx in selected_rows]
        selected_paths = [p for p in selected_paths if os.path.exists(p)]
        
        # Unione dei due insiemi (mantenendo l'ordine dei file)
        files_to_move = []
        seen = set()
        
        # Diamo la precedenza ai file spuntati, se presenti
        source_list = checked_files if checked_files else selected_paths
        for p in source_list:
            if p not in seen:
                seen.add(p)
                files_to_move.append(p)
                
        if not files_to_move:
            QMessageBox.information(self, "Info", "Seleziona o spunta uno o più file dall'elenco a sinistra per spostarli.")
            return
            
        # Determina directory di partenza per il dialogo
        start_dir = os.path.dirname(files_to_move[0]) if files_to_move else self.current_folder_path
        
        dest_dir = QFileDialog.getExistingDirectory(self, "Seleziona cartella di destinazione", start_dir)
        if dest_dir:
            reply = QMessageBox.question(
                self, "Conferma Spostamento", 
                f"Sei sicuro di voler spostare {len(files_to_move)} elementi nella cartella:\n{dest_dir}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # Libera i lock svuotando l'anteprima
                self.clear_viewer()
                QApplication.setOverrideCursor(Qt.WaitCursor)
                self.btn_sidebar_move.setEnabled(False)
                
                # Esegui lo spostamento asincrono usando MoveWorker
                self.move_worker = MoveWorker(files_to_move, dest_dir)
                self.move_worker.work_finished.connect(self.on_sidebar_move_finished)
                self.move_worker.error.connect(self.on_sidebar_move_error)
                self.move_worker.start()

    def on_sidebar_move_finished(self, moved_count):
        from PySide6.QtWidgets import QApplication, QMessageBox
        QApplication.restoreOverrideCursor()
        self.btn_sidebar_move.setEnabled(True)
        self.file_model.clear_checked()
        QMessageBox.information(self, "Spostamento Completato", f"{moved_count} elementi spostati con successo!")
        self.refresh_tree()
        self.clear_viewer()
        
    def on_sidebar_move_error(self, err_msg):
        from PySide6.QtWidgets import QApplication, QMessageBox
        QApplication.restoreOverrideCursor()
        self.btn_sidebar_move.setEnabled(True)
        QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento: {err_msg}")

    def action_move_current(self):
        filepath = self.get_current_filepath()
        if not filepath: return
        
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QApplication
        start_dir = os.path.dirname(filepath)
        dest_dir = QFileDialog.getExistingDirectory(self, "Seleziona cartella di destinazione", start_dir)
        if dest_dir:
            reply = QMessageBox.question(
                self, "Conferma Spostamento", 
                f"Sei sicuro di voler spostare questa foto nella cartella:\n{dest_dir}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # Libera il visualizzatore e sblocca il file
                self.clear_viewer()
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    from core.batch_actions import move_media_files
                    moved = move_media_files([filepath], dest_dir)
                    if moved > 0:
                        QMessageBox.information(self, "Spostamento Completato", "File spostato con successo!")
                        self.refresh_tree()
                        self.clear_viewer()
                    else:
                        QMessageBox.warning(self, "Errore", "Impossibile spostare il file.")
                except Exception as e:
                    QMessageBox.warning(self, "Errore", f"Errore durante lo spostamento: {e}")
                finally:
                    QApplication.restoreOverrideCursor()
