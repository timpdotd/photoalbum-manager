import sys
import os

# Disabilita log e spam in console di FFmpeg e OpenCV su file video corrotti o strani
os.environ["OPENCV_FFMPEG_LOGLEVEL"] = "-8"
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["OPENCV_VIDEOIO_DEBUG"] = "0"

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    # Ottieni la cartella principale del progetto
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Configura il logger centrale (si resetta ad ogni avvio)
    from core.logger import setup_logger
    setup_logger(project_dir)
    
    # Crea l'applicazione Qt
    app = QApplication(sys.argv)
    
    # Crea ed mostra la finestra principale
    window = MainWindow(project_dir)
    window.show()
    
    # Avvia l'event loop di Qt
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
