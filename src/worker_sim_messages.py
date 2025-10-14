import json
import logging
import re
import traceback
from threading import Event
from PySide6.QtCore import Signal
from src.worker_base import WorkerBase
from src.worker_screenshot_device_base import WorkerScreenshotBase


class WorkerSimMessages(WorkerBase):
    player_info = 201
    club_selected = Signal(object)
    sim_message = Signal(object)

    def __init__(self, sim_connect):
        super().__init__()
        self.sim_connect = sim_connect
        self.name = 'WorkerSimMessages'

    def run(self):
        self.started.emit()
        logging.debug(f'{self.name} Started')
        # Execute if not shutdown
        while not self._shutdown.is_set():
            Event().wait(250/1000)
            # When _pause is clear we wait(suspended) if set we process
            self._pause.wait()
            if not self._shutdown.is_set() and self.sim_connect is not None and self.sim_connect.connected():
                try:
                    message = self.sim_connect.check_for_message()
                    if len(message) > 0:
                        logging.debug(f'{self.name}: Received data: {message}')
                        self.sim_message.emit(message)
                        self.__process_message(message)
                except Exception as e:
                    if not isinstance(e, ValueError):
                        self.pause()
                    traceback.print_exc()
                    logging.debug(f'Error in process {self.name}: {format(e)}, {traceback.format_exc()}')
                    self.error.emit((e, traceback.format_exc()))
        self.finished.emit()

    def __process_message(self, message):
        messages = {}
        json_messages = re.split(r'(\{.*?})(?= *\{)', message.decode("utf-8"))
        for json_message in json_messages:
            if len(json_message) > 0:
                logging.debug(f'__process_message json_message: {json_message}')
                msg = json.loads(json_message)
                messages[str(msg['Code'])] = msg
                # Check if club selection message
                if msg['Code'] == WorkerSimMessages.player_info:
                    self.club_selected.emit(msg)
        return messages
