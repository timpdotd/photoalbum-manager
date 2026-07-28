from PySide6.QtCore import QThread, Signal
from core.batch_actions import execute_save

class SaveWorker(QThread):
    work_finished = Signal()
    error = Signal(str)

    def __init__(self, pending_actions):
        super().__init__()
        self.pending_actions = pending_actions

    def run(self):
        try:
            execute_save(self.pending_actions)
            self.work_finished.emit()
        except Exception as e:
            self.error.emit(str(e))
