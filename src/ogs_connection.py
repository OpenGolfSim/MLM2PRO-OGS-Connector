import logging
import os

from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QMessageBox
from src.ctype_screenshot import ScreenMirrorWindow
from src.ogs_connect import OpenGolfSimConnect
from src.worker_ogs_messages import WorkerOpenGolfSimMessages
# from src.worker_gspro_start import WorkerGSProStart
from src.worker_ogs import WorkerOpenGolfSim
from src.log_message import LogMessageSystems, LogMessageTypes
from src.worker_thread import WorkerThread
from PySide6.QtCore import QProcess

class OpenGolfSimConnection(QObject):
    connected_to_ogs = Signal()
    disconnected_from_ogs = Signal()
    club_selected = Signal(object)
    ogs_message = Signal(object)

    def __init__(self, main_window):
        super(OpenGolfSimConnection, self).__init__()
        self.main_window = main_window
        self.current_club = None
        self.worker = None
        self.thread = None
        self.ogs_messages_thread = None
        self.ogs_messages_worker = None
        self.send_shot_thread = None
        self.send_shot_worker = None
        self.ogs_start_worker = None
        self.ogs_start_thread = None
        self.connected = False
        self.settings = main_window.settings
        self.ogs_connect = OpenGolfSimConnect(
            self.settings.device_id,
            self.settings.units,
            self.settings.api_version
        )
        self.__ogs_disconnected()
        self.__setup_send_shot_thread()
        self.__setup_ogs_messages_thread()    


    def __ogs_disconnected(self):
        self.main_window.gspro_connect_button.setEnabled(True)
        self.main_window.log_message(LogMessageTypes.ALL, LogMessageSystems.GSPRO_CONNECT, 'Disconnected from OpenGolfSim')
        self.main_window.gspro_connect_button.setText('Connect')
        self.main_window.gspro_status_label.setText('Not Connected')
        self.main_window.gspro_status_label.setStyleSheet(f"QLabel {{ background-color : red; color : white; }}")

    def __setup_send_shot_thread(self):
        self.send_shot_thread = QThread()
        self.send_shot_worker = WorkerOpenGolfSim(self.ogs_connect)
        self.send_shot_worker.moveToThread(self.send_shot_thread)
        self.send_shot_worker.started.connect(self.__sending_shot)
        self.send_shot_worker.sent.connect(self.main_window.shot_sent)
        self.send_shot_worker.error.connect(self.__send_shot_error)
        self.send_shot_thread.started.connect(self.send_shot_worker.run)
        self.send_shot_thread.start()

    def __setup_ogs_messages_thread(self):
        self.ogs_messages_thread = QThread()
        self.ogs_messages_worker = WorkerOpenGolfSimMessages(self.ogs_connect)
        self.ogs_messages_worker.moveToThread(self.ogs_messages_thread)
        self.ogs_messages_worker.club_selected.connect(self.__club_selected)
        self.ogs_messages_worker.error.connect(self.__ogs_messages_error)
        self.ogs_messages_worker.ogs_message.connect(self.__ogs_message)
        self.ogs_messages_thread.started.connect(self.ogs_messages_worker.run)
        self.ogs_messages_thread.start()

    def __ogs_message(self, message):
        self.ogs_message.emit(message)

    def __setup_connection_thread(self):
        self.thread = QThread()
        self.worker = WorkerThread(self.ogs_connect.init_socket, self.settings.ogs_ip_address, self.settings.ogs_port)
        self.worker.moveToThread(self.thread)
        self.worker.started.connect(self.__in_progress)
        self.worker.result.connect(self.__connected)
        self.worker.error.connect(self.__error)
        # self.worker.finished.connect(self.__finished)
        self.thread.started.connect(self.worker.run())
        self.thread.start()

    def __club_selecion_error(self, error):
        self.disconnect_from_ogs()
        msg = f"Error while trying to check for club selection messages from GSPro.\nMake sure GSPro API Connect is running.\nStart/restart API Connect from GSPro.\nPress 'Connect' to reconnect to GSPro."
        self.__log_message(LogMessageTypes.LOGS, f'{msg}\nException: {format(error)}')
        QMessageBox.warning(self.main_window, "GSPro Receive Error", msg)

    def __club_selected(self, club_data):
        logging.debug(f"{self.__class__.__name__} Club selected: {club_data['Player']['Club']}")
        if club_data['Player']['Club'] == "PT":
            self.main_window.club_selection.setText('Putter')
            self.main_window.club_selection.setStyleSheet(f"QLabel {{ background-color : green; color : white; }}")
        else:
            self.main_window.club_selection.setText(club_data['Player']['Club'])
            self.main_window.club_selection.setStyleSheet(f"QLabel {{ background-color : orange; color : white; }}")
        self.club_selected.emit(club_data)
        if self.current_club != club_data['Player']['Club']:
            self.main_window.log_message(LogMessageTypes.ALL, LogMessageSystems.CONNECTOR, f'Club selected: {club_data["Player"]["Club"]}')
            self.current_club = club_data['Player']['Club']

    def __send_shot_error(self, error):
        self.disconnect_from_ogs()
        msg = f"Error while trying to send shot to GSPro.\nMake sure GSPro API Connect is running.\nStart/restart API Connect from GSPro.\nPress 'Connect' to reconnect to GSPro."
        self.__log_message(LogMessageTypes.LOGS, f'{msg}\nException: {format(error)}')
        QMessageBox.warning(self.main_window, "GSPro Send Error", msg)

    def __ogs_messages_error(self, error):
        self.disconnect_from_ogs()
        msg = f"Error while trying to check for new messages from GSPro.\nStart/restart API Connect from GSPro.\nPress 'Connect' to reconnect to GSPro."
        self.__log_message(LogMessageTypes.LOGS, f'{msg}\nException: {format(error)}')
        QMessageBox.warning(self.main_window, "GSPro Message Receive Error", msg)

    def connect_to_ogs(self):
        if not self.connected:
            # if self.__find_gspro_api_app():
            if self.thread is None:
                self.__setup_connection_thread()
            else:
                if not self.ogs_connect.connected():
                    self.worker.run()
            if self.ogs_messages_thread is None:
                self.__setup_ogs_messages_thread()
            self.ogs_messages_worker.start()
            if self.send_shot_thread is None:
                self.__setup_send_shot_thread()
            self.send_shot_worker.start()
            # self.__shutdown_ogs_start_thread()

    def disconnect_from_ogs(self):
        if self.connected:
            self.connected = False
            self.__ogs_disconnected()
            self.send_shot_worker.stop()
            self.ogs_messages_worker.stop()
            self.ogs_connect.terminate_session()
            self.disconnected_from_ogs.emit()

    def __sending_shot(self):
        self.__log_message(LogMessageTypes.ALL, 'Sending shot to GSPro')

    def __in_progress(self):
        msg = 'Connecting...'
        self.__log_message(LogMessageTypes.ALL, f'Connecting to GSPro...')
        self.__log_message(LogMessageTypes.LOGS, f'Connection settings: {self.settings.to_json(True)}')
        self.main_window.gspro_status_label.setText(msg)
        self.main_window.gspro_status_label.setStyleSheet("QLabel { background-color : orange; color : white; }")
        self.main_window.gspro_connect_button.setEnabled(False)

    def __connected(self):
        self.connected = True
        self.main_window.gspro_connect_button.setEnabled(True)
        self.main_window.log_message(LogMessageTypes.ALL, LogMessageSystems.GSPRO_CONNECT, f'Connected to OpenGolfSim')
        self.main_window.gspro_connect_button.setText('Disconnect')
        self.main_window.gspro_status_label.setText('Connected')
        self.main_window.gspro_status_label.setStyleSheet(f"QLabel {{ background-color : green; color : white; }}")
        self.connected_to_ogs.emit()

    def __error(self, error):
        self.disconnect_from_ogs()
        msg = "Error while trying to connect to OpenGolfSim.\nMake sure OpenGolfSim API Connect is running.\nStart/restart API Connect from OpenGolfSim.\nPress 'Connect' to reconnect to OpenGolfSim."
        self.__log_message(LogMessageTypes.LOGS, f'{msg} Exception: {format(error)}')
        QMessageBox.warning(self.main_window, "OpenGolfSim Connect Error", msg)

    def shutdown(self):
        self.ogs_connect.terminate_session()
        self.connected = False
        self.__shutdown_threads()

    def __log_message(self, types, message):
        self.main_window.log_message(types, LogMessageSystems.OPENGOLFSIM, message)

    def __shutdown_threads(self):
        if self.ogs_messages_thread is not None:
            self.ogs_messages_worker.shutdown()
            self.ogs_messages_thread.quit()
            self.ogs_messages_thread.wait()
            self.ogs_messages_thread = None
            self.ogs_messages_worker = None
        if self.send_shot_thread is not None:
            self.send_shot_thread.quit()
            self.send_shot_thread.wait()
            self.send_shot_thread = None
            self.send_shot_worker = None
        if self.thread is not None:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
            self.worker = None

    def __shutdown_ogs_start_thread(self):
        logging.debug(f'{self.__class__.__name__} Shutting down threads, ogs_start_thread')
        if self.ogs_start_thread is not None:
            self.ogs_start_worker.shutdown()
            if self.ogs_start_thread.isRunning():
                logging.debug(f'{self.__class__.__name__} Quitting ogs_start_thread')
                self.ogs_start_thread.quit()
                self.ogs_start_thread.wait()
            self.ogs_start_thread = None
            self.ogs_start_worker = None
