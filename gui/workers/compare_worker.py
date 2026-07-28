from PySide6.QtCore import QThread, Signal
from core.comparer import Comparer

class CompareWorker(QThread):
    progress = Signal(int)
    work_finished = Signal(dict)
    error = Signal(str)

    def __init__(self, target_folder, root_path, hash_tol):
        super().__init__()
        self.comparer = Comparer(
            target_folder=target_folder,
            root_path=root_path,
            hash_tol=hash_tol
        )

    def run(self):
        try:
            groups = self.comparer.run(self.progress.emit)
            self.work_finished.emit(groups)
        except Exception as e:
            self.error.emit(str(e))
