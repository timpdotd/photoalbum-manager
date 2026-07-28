import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QFrame,
    QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt
from gui.viewer_tab import ViewerTab
from gui.dashboard_tab import DashboardTab
from gui.duplicates_tab import DuplicatesTab
from gui.style import DARK_STYLESHEET

class MainWindow(QMainWindow):
    def __init__(self, workspace_path):
        super().__init__()
        self.setWindowTitle("Photoalbum Orderer")
        self.resize(1150, 750)
        
        # Imposta la cartella iniziale di default
        self.workspace_path = workspace_path
        self.default_scan_path = os.path.join(workspace_path, "TEST")
        if not os.path.exists(self.default_scan_path):
            self.default_scan_path = workspace_path
            
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        # Widget centrale
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principale verticale
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SELETTORE CARTELLA IN ALTO A TUTTA LARGHEZZA (Completamente sopra) ---
        path_frame = QFrame()
        path_frame.setObjectName("sidebarPanel") # Stile scuro
        path_frame.setStyleSheet("border-radius: 0px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);")
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(20, 10, 20, 10)
        path_layout.setSpacing(10)

        path_lbl = QLabel("Cartella di Input:")
        path_lbl.setStyleSheet("font-weight: bold; color: #9ca3af; font-size: 13px; border: none;")
        path_layout.addWidget(path_lbl)

        self.path_input = QLineEdit(self.default_scan_path)
        self.path_input.setReadOnly(True)
        path_layout.addWidget(self.path_input)

        self.btn_browse = QPushButton("...")
        self.btn_browse.setObjectName("btnRefresh")
        self.btn_browse.setFixedWidth(40)
        self.btn_browse.setToolTip("Seleziona un'altra cartella")
        self.btn_browse.clicked.connect(self.choose_folder)
        path_layout.addWidget(self.btn_browse)

        self.btn_refresh = QPushButton("🔄 Ricarica")
        self.btn_refresh.setObjectName("btnRefresh")
        self.btn_refresh.setToolTip("Ricarica cartella")
        self.btn_refresh.clicked.connect(self.refresh_folder)
        path_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(path_frame)

        # --- NAVIGATION BAR (Header) ---
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_frame.setStyleSheet("""
            background-color: #111827; 
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # Logo sinistra
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🖼️")
        logo_icon.setStyleSheet("font-size: 22px;")
        logo_title = QLabel("Photoalbum Orderer")
        logo_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f3f4f6;")
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_title)
        header_layout.addLayout(logo_layout)

        header_layout.addStretch()

        # Bottoni di navigazione centrali (Tabs customizzati)
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.btn_viewer = QPushButton("📁 Visualizzatore Foto")
        self.btn_viewer.setCursor(Qt.PointingHandCursor)
        self.btn_viewer.clicked.connect(lambda: self.switch_tab(0))
        nav_layout.addWidget(self.btn_viewer)

        self.btn_dashboard = QPushButton("📊 Dashboard Processi")
        self.btn_dashboard.setCursor(Qt.PointingHandCursor)
        self.btn_dashboard.clicked.connect(lambda: self.switch_tab(1))
        nav_layout.addWidget(self.btn_dashboard)

        self.btn_duplicates = QPushButton("🔍 Duplicati")
        self.btn_duplicates.setCursor(Qt.PointingHandCursor)
        self.btn_duplicates.clicked.connect(lambda: self.switch_tab(2))
        nav_layout.addWidget(self.btn_duplicates)

        header_layout.addLayout(nav_layout)
        header_layout.addStretch() # bilancia i lati

        main_layout.addWidget(header_frame)

        # --- STACKED WIDGET (Pagine principali) ---
        self.stacked_widget = QStackedWidget()
        
        self.viewer_tab = ViewerTab(self.default_scan_path)
        self.dashboard_tab = DashboardTab(self.default_scan_path)
        self.duplicates_tab = DuplicatesTab(self.workspace_path)
        
        self.stacked_widget.addWidget(self.viewer_tab)
        self.stacked_widget.addWidget(self.dashboard_tab)
        self.stacked_widget.addWidget(self.duplicates_tab)
        
        main_layout.addWidget(self.stacked_widget)

        # Seleziona il primo tab all'avvio
        self.switch_tab(0)

        # Avvia scansione base automatica all'avvio
        self.dashboard_tab.start_process("basic")

    def switch_tab(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
        # Stili dinamici dei bottoni in base alla scheda attiva
        active_style = """
            background-color: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid #6366f1;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
        """
        inactive_style = """
            background-color: transparent;
            color: #9ca3af;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 500;
        """

        if index == 0:
            self.btn_viewer.setStyleSheet(active_style)
            self.btn_dashboard.setStyleSheet(inactive_style)
            self.btn_duplicates.setStyleSheet(inactive_style)
        elif index == 1:
            self.btn_viewer.setStyleSheet(inactive_style)
            self.btn_dashboard.setStyleSheet(active_style)
            self.btn_duplicates.setStyleSheet(inactive_style)
        else:
            self.btn_viewer.setStyleSheet(inactive_style)
            self.btn_dashboard.setStyleSheet(inactive_style)
            self.btn_duplicates.setStyleSheet(active_style)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleziona cartella di input", self.default_scan_path)
        if folder:
            self.default_scan_path = folder
            self.path_input.setText(folder)
            self.viewer_tab.set_folder_path(folder)
            self.dashboard_tab.set_folder_path(folder)
            self.duplicates_tab.set_folder_path(folder)

    def refresh_folder(self):
        self.viewer_tab.refresh_tree()

    def apply_styles(self):
        # Applica il foglio di stile QSS a livello di finestra
        self.setStyleSheet(DARK_STYLESHEET)

    def closeEvent(self, event):
        # Quando l'applicazione si chiude, esegui il controllo e la numerazione sequenziale
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from core.scanner import find_image_folders
        from core.image_processor import process_folder
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Trova tutte le cartelle contenenti immagini a partire dalla cartella di input corrente
            folders = find_image_folders(self.default_scan_path)
            for folder in folders:
                process_folder(folder)
        except Exception as e:
            print(f"Errore durante il salvataggio alla chiusura dell'applicazione: {e}")
        finally:
            QApplication.restoreOverrideCursor()
            
        event.accept()


