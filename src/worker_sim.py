import traceback
from PySide6.QtCore import Signal

from src.worker_base import WorkerBase


class WorkerSim(WorkerBase):
    sent = Signal(object or None)

    def __init__(self, sim_connect):
        super().__init__()
        self.sim_connect = sim_connect

    def run(self, balldata=None):
        if balldata is not None:
            try:
                print(f'WorkerSim: {balldata.to_json()}')
                self.started.emit()
                self.sim_connect.launch_ball(balldata)
            except Exception as e:
                traceback.print_exc()
                self.error.emit((e, traceback.format_exc()))
            else:
                self.sent.emit(balldata)  # Return the result of the processing
            finally:
                self.finished.emit()  # Done
                