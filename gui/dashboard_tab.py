from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QProgressBar, QPushButton, QFrame, QListWidget, QListWidgetItem,
    QCheckBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from gui.workers.worker import ProcessWorker

class ProcessCard(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardCard")
        self.init_ui(name)

    def init_ui(self, name):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header: Nome e Badge di Stato
        header_layout = QHBoxLayout()
        self.lbl_name = QLabel(name)
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #f3f4f6;")
        header_layout.addWidget(self.lbl_name)

        self.lbl_status = QLabel("IN ATTESA")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.set_status_badge("in_attesa")
        header_layout.addWidget(self.lbl_status)
        layout.addLayout(header_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        layout.addWidget(self.progress_bar)

        # Ultimo messaggio
        self.lbl_message = QLabel("In attesa dell'avvio...")
        self.lbl_message.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(self.lbl_message)

    def set_status_badge(self, status):
        if status == "completato":
            self.lbl_status.setText("COMPLETATO")
            self.lbl_status.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.2); 
                color: #10b981; 
                border: 1px solid #10b981;
                border-radius: 4px; 
                padding: 2px 8px; 
                font-size: 11px; 
                font-weight: bold;
            """)
        elif status == "in_corso":
            self.lbl_status.setText("IN CORSO")
            self.lbl_status.setStyleSheet("""
                background-color: rgba(99, 102, 241, 0.2); 
                color: #818cf8; 
                border: 1px solid #6366f1;
                border-radius: 4px; 
                padding: 2px 8px; 
                font-size: 11px; 
                font-weight: bold;
            """)
        else: # in_attesa
            self.lbl_status.setText("IN ATTESA")
            self.lbl_status.setStyleSheet("""
                background-color: rgba(107, 114, 128, 0.2); 
                color: #9ca3af; 
                border: 1px solid #6b7280;
                border-radius: 4px; 
                padding: 2px 8px; 
                font-size: 11px; 
                font-weight: bold;
            """)

    def update_progress(self, progress, status, message):
        self.progress_bar.setValue(progress)
        self.set_status_badge(status)
        self.lbl_message.setText(message)

class DashboardTab(QWidget):
    def __init__(self, input_folder, parent=None):
        super().__init__(parent)
        self.worker = None
        self.input_folder = input_folder
        self.init_ui()

    def set_folder_path(self, folder):
        self.input_folder = folder
        self.log_event(f"Cartella di input aggiornata: {folder}")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Header della Dashboard
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        
        main_title = QLabel("Stato dei Processi di Backend")
        main_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f3f4f6;")
        title_layout.addWidget(main_title)
        
        subtitle = QLabel("Visualizzazione e monitoraggio dei flussi di lavoro in esecuzione")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13px;")
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)

        # Pulsanti Azione
        buttons_layout = QHBoxLayout()
        
        self.btn_basic = QPushButton("⚡ Scansione Base (Printed & CSV)")
        self.btn_basic.setObjectName("btnTriggerDemo")
        self.btn_basic.clicked.connect(lambda: self.start_process("basic"))
        buttons_layout.addWidget(self.btn_basic)

        self.btn_hash = QPushButton("🧬 Calcola Hash Ibrido (pHash + Colori)")
        self.btn_hash.setObjectName("btnTriggerDemo")
        self.btn_hash.clicked.connect(lambda: self.start_process("hash"))
        buttons_layout.addWidget(self.btn_hash)

        header_layout.addLayout(buttons_layout)
        
        # Checkbox per forzare il riprocessamento
        self.chk_force = QCheckBox("Forza riprocessamento (ignora cache)")
        self.chk_force.setStyleSheet("color: #9ca3af; margin-top: 5px;")
        title_layout.addWidget(self.chk_force)
        
        main_layout.addLayout(header_layout)

        # Grid dei Processi
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        self.cards = {
            "scan_dir": ProcessCard("Esplorazione Cartella"),
            "process_img": ProcessCard("Elaborazione Immagini"),
            "db_update": ProcessCard("Salvataggio Database")
        }

        # Impostiamo di default "Esplorazione Cartella" come completato
        self.cards["scan_dir"].update_progress(100, "completato", "Pronto.")

        grid_layout.addWidget(self.cards["scan_dir"], 0, 0)
        grid_layout.addWidget(self.cards["process_img"], 0, 1)
        grid_layout.addWidget(self.cards["db_update"], 1, 0, 1, 2) # spanning wide

        main_layout.addLayout(grid_layout)

        # Console di Log
        console_title = QLabel("Console Log Attività")
        console_title.setObjectName("sectionTitle")
        main_layout.addWidget(console_title)

        self.log_list = QListWidget()
        self.log_list.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        main_layout.addWidget(self.log_list)

        # Collega il logger centrale alla console
        from core.logger import get_logger, QListWidgetLogHandler
        logger = get_logger()
        for h in logger.handlers:
            if isinstance(h, QListWidgetLogHandler):
                h.signaller.log_signal.connect(self.log_event_from_signal)
                break

        self.log_event("Sistema GUI pronto. In attesa di avvio dei processi.")

    def log_event_from_signal(self, text):
        item = QListWidgetItem(text)
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def log_event(self, text):
        from core.logger import get_logger
        get_logger().info(text)

    def set_buttons_enabled(self, enabled):
        self.btn_basic.setEnabled(enabled)
        self.btn_hash.setEnabled(enabled)

    def start_process(self, task_type):
        self.set_buttons_enabled(False)
        self.log_event(f"Avvio processo: {task_type}...")
        
        # Reset card status
        self.cards["scan_dir"].update_progress(0, "in_corso", "Ricerca cartelle...")
        self.cards["process_img"].update_progress(0, "in_attesa", "In attesa...")
        self.cards["db_update"].update_progress(0, "in_attesa", "In attesa...")

        # Creazione e avvio del Thread Worker
        self.worker = ProcessWorker(self.input_folder, task_type, force=self.chk_force.isChecked())
        self.worker.progress_changed.connect(self.on_worker_progress)
        self.worker.work_finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_progress(self, proc_id, progress, status, message):
        if proc_id in self.cards:
            self.cards[proc_id].update_progress(progress, status, message)
            self.log_event(f"{self.cards[proc_id].lbl_name.text()}: {message}")

    def on_worker_finished(self):
        self.set_buttons_enabled(True)
        self.log_event("Processo completato.")
