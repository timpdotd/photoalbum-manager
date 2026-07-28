# Stylizzazione QSS Premium per Photoalbum Orderer

DARK_STYLESHEET = """
/* Stile globale */
QWidget {
    background-color: #0b0f19;
    color: #f3f4f6;
    font-family: "Segoe UI", "Outfit", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

/* Finestra principale e container */
QMainWindow {
    background-color: #0b0f19;
}

/* Pannelli con effetto Glassmorphism/Surface */
QFrame#sidebarPanel, QFrame#viewerPanel, QFrame#metaPanel, QFrame#dashboardCard {
    background-color: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
}

/* Intestazioni e Titoli */
QLabel#headerTitle {
    font-size: 18px;
    font-weight: bold;
    color: #f3f4f6;
    padding: 5px;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 600;
    color: #f3f4f6;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 4px;
}

/* Tab Widget modernizzato */
QTabWidget::pane {
    border: none;
    background-color: #0b0f19;
}

QTabBar::tab {
    background-color: #111827;
    color: #9ca3af;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 4px;
    font-weight: 500;
}

QTabBar::tab:hover {
    background-color: #1f2937;
    color: #f3f4f6;
}

QTabBar::tab:selected {
    background-color: #1f2937;
    color: #6366f1;
    border-bottom: 2px solid #6366f1;
    font-weight: 600;
}

/* Bottoni Premium */
QPushButton {
    background-color: #6366f1;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #4f46e5;
}

QPushButton:pressed {
    background-color: #4338ca;
}

QPushButton:disabled {
    background-color: #374151;
    color: #9ca3af;
}

/* Bottone secondario o Refresh */
QPushButton#btnRefresh, QPushButton#btnTriggerDemo {
    background-color: #1f2937;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #f3f4f6;
}

QPushButton#btnRefresh:hover, QPushButton#btnTriggerDemo:hover {
    background-color: #374151;
    border-color: rgba(255, 255, 255, 0.2);
}

QPushButton#btnTriggerDemo {
    background-color: #6366f1; /* mantiene colore primario per trigger */
    border: none;
}

QPushButton#btnTriggerDemo:hover {
    background-color: #4f46e5;
}

/* File Explorer Tree View */
QTreeView {
    background-color: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 5px;
    show-decoration-selected: 1;
}

QTreeView::item {
    padding: 6px;
    border-radius: 4px;
    color: #d1d5db;
}

QTreeView::item:hover {
    background-color: rgba(255, 255, 255, 0.04);
    color: #f3f4f6;
}

QTreeView::item:selected {
    background-color: rgba(99, 102, 241, 0.2);
    color: #818cf8;
    border-left: 3px solid #6366f1;
}

QTreeView::branch:has-children:!has-depth:closed,
QTreeView::branch:has-children:has-depth:closed {
    border-image: none;
    image: url(none); /* standard dropdown can show icons */
}

/* Input di testo e percorsi */
QLineEdit {
    background-color: #1f2937;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 6px 10px;
    color: #f3f4f6;
}

QLineEdit:focus {
    border: 1px solid #6366f1;
}

/* ScrollArea per visualizzatore immagini */
QScrollArea {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    background-color: #111827;
}

QScrollArea QWidget {
    background-color: #111827;
}

/* Progress Bar moderna */
QProgressBar {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    background-color: #1f2937;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                      stop:0 #6366f1, stop:1 #10b981);
    border-radius: 5px;
}

/* Scrollbar personalizzate sottili */
QScrollBar:vertical {
    border: none;
    background: #0b0f19;
    width: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.1);
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.2);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: #0b0f19;
    height: 8px;
    margin: 0px 0px 0px 0px;
}

QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.1);
    min-width: 20px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.2);
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
}

/* Log Console o List Widget */
QListWidget {
    background-color: #111827;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 8px;
    color: #e5e7eb;
}

QListWidget::item {
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    padding: 4px;
}

QListWidget::item:last {
    border-bottom: none;
}
"""
