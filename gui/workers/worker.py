import time
from PySide6.QtCore import QThread, Signal
from core.scanner import find_image_folders
from core.image_processor import process_folder
from core.hash_processor import process_perceptual_hash

class ProcessWorker(QThread):
    # Segnale emesso per ogni avanzamento: (id_processo, progresso, stato, messaggio)
    progress_changed = Signal(str, int, str, str)
    work_finished = Signal()

    def __init__(self, root_path, task_type="basic", force=False, parent=None):
        super().__init__(parent)
        self.root_path = root_path
        self.task_type = task_type
        self.force = force
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        # 1. Scansione directory
        self.progress_changed.emit("scan_dir", 0, "in_corso", "Ricerca cartelle con immagini...")
        
        try:
            image_folders = find_image_folders(self.root_path)
            total_folders = len(image_folders)
            
            if total_folders == 0:
                self.progress_changed.emit("scan_dir", 100, "completato", "Nessuna cartella con immagini trovata.")
                self.progress_changed.emit("process_img", 100, "completato", "Nessuna elaborazione necessaria.")
                self.progress_changed.emit("db_update", 100, "completato", "Processo terminato.")
                self.finished.emit()
                return

            self.progress_changed.emit("scan_dir", 100, "completato", f"Trovate {total_folders} cartelle.")
            
            if not self._is_running:
                return

            # 2. Elaborazione cartelle
            task_names = {
                "basic": "Elaborazione base (Cartelle Printed & CSV)",
                "hash": "Calcolo Hash Ibrido (pHash+Colori)"
            }
            task_name = task_names.get(self.task_type, "Elaborazione")
            self.progress_changed.emit("process_img", 0, "in_corso", f"Avvio {task_name}...")
            
            total_processed = 0
            for i, folder in enumerate(image_folders):
                if not self._is_running:
                    return
                
                # Elabora in base al tipo di task
                num_processed = 0
                if self.task_type == "basic":
                    num_processed = process_folder(folder)
                elif self.task_type == "hash":
                    num_processed = process_perceptual_hash(folder, force=self.force)
                    
                total_processed += num_processed
                
                # Calcola progresso
                progress = int(((i + 1) / total_folders) * 100)
                msg = f"Elaborata cartella {i + 1}/{total_folders} ({num_processed} elementi elaborati)..."
                
                if progress == 100:
                    msg = f"{task_name} completata. ({total_processed} tot. elaborati)"
                    
                self.progress_changed.emit("process_img", progress, "in_corso" if progress < 100 else "completato", msg)
                time.sleep(0.05)  # Piccola pausa per far respirare la UI

            if not self._is_running:
                return

            # 3. Aggiornamento Database
            self.progress_changed.emit("db_update", 0, "in_corso", "Salvataggio nel database in corso...")
            time.sleep(0.2)
            self.progress_changed.emit("db_update", 100, "completato", "Database aggiornato correttamente.")
            
        except Exception as e:
            # Gestione basica errori
            self.progress_changed.emit("scan_dir", 0, "in_attesa", f"Errore: {str(e)}")
            
        finally:
            self.work_finished.emit()
