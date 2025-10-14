import socket
import logging
import json
from threading import Event

import select
from PySide6.QtCore import QObject

from src.ball_data import BallData
from src.custom_exception import SimTCPConnectionTimeout, SimTCPConnectionUnknownError, \
    SimTCPConnectionClientClosedConnection, SimTCPConnectionSocketError


class ConnectBase(QObject):

    successful_send = 200

    def __init__(self, device_id, units, api_version) -> None:
        self._socket = None
        self._device_id = device_id
        self._units = units
        self._api_version = api_version
        self._shot_number = 1
        self._connected = False
        super(ConnectBase, self).__init__()

    def init_socket(self, ip_address: str, port: int) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((ip_address, port))
        self._socket.settimeout(2)
        self._connected = True

    def connected(self):
        return self._connected

    def send_msg(self, payload, attempts=2):
        if self._connected:
            for attempt in range(attempts):
                try:
                    logging.info(f"Sending to GSPro data: {payload}")
                    self._socket.sendall(payload)
                    msg = self._socket.recv(2048)
                except socket.timeout:
                    logging.info('Timed out. Retrying...')
                    if attempt >= attempts-1:
                        raise SimTCPConnectionTimeout(f'Failed to send shot to simulator after {attempts} attempts.')
                    Event().wait(0.5)
                    continue
                except socket.error as e:
                    msg = f'Socket error when trying to send shot to simulator, Exception: {format(e)}'
                    logging.debug(msg)
                    raise SimTCPConnectionSocketError(msg)
                except Exception as e:
                    msg = f"Unknown error when trying to send shot to simulator, Exception: {format(e)}"
                    logging.debug(msg)
                    raise SimTCPConnectionUnknownError(msg)
                else:
                    if len(msg) == 0:
                        msg = f"Simulator closed the connection"
                        logging.debug(msg)
                        raise SimTCPConnectionClientClosedConnection(msg)
                    else:
                        logging.debug(f"Response from simulator: {msg}")
                        return msg

    def launch_ball(self, ball_data: BallData) -> None:
        # logging.debug(f"---- launch_ball -----")
        print("---------base_launch_ball")
        logging.debug(ball_data)
        return

    def check_for_message(self):
        message = bytes(0)
        if self._connected:
            read_socket, write_socket, error_socket = select.select([self._socket], [], [], 0)
            while read_socket:
                message = message + self._socket.recv(1024)
                read_socket, write_socket, error_socket = select.select([self._socket], [], [], 0)
        return message

    def terminate_session(self):
        if self._socket:
            self._socket.close()
            self._connected = False
