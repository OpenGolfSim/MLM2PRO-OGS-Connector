import traceback
from PySide6.QtCore import Signal

from src.ogs_connect import OpenGolfSimConnect
from src.worker_base import WorkerBase


class WorkerOpenGolfSim(WorkerBase):
    sent = Signal(object or None)

    def __init__(self, ogs_connection: OpenGolfSimConnect):
        super().__init__()
        self.ogs_connection = ogs_connection

    def run(self, balldata=None):
        if balldata is not None:
            try:
                self.started.emit()
                self.ogs_connection.launch_ball(balldata)
            except Exception as e:
                traceback.print_exc()
                self.error.emit((e, traceback.format_exc()))
            else:
                self.sent.emit(balldata)  # Return the result of the processing
            finally:
                self.finished.emit()  # Done
                