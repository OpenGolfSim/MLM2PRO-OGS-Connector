import socket
import logging
import json
from threading import Event

import select
from PySide6.QtCore import QObject

from src.connect_base import ConnectBase
from src.ball_data import BallData
from src.custom_exception import SimTCPConnectionTimeout, SimTCPConnectionUnknownError, \
    SimTCPConnectionClientClosedConnection, SimTCPConnectionSocketError


class OpenGolfSimConnect(ConnectBase):

    successful_send = 200

    def __init__(self) -> None:
        self._socket = None
        self._shot_number = 1
        self._connected = False
        super(ConnectBase, self).__init__()

    def send_msg(self, payload, attempts=2):
        if self._connected:
            for attempt in range(attempts):
                try:
                    logging.info(f"Sending data: {payload}")
                    self._socket.sendall(payload)
                    msg = self._socket.recv(2048)
                except socket.timeout:
                    logging.info('Timed out. Retrying...')
                    if attempt >= attempts-1:
                        raise SimTCPConnectionTimeout(f'Failed to send shot to OpenGolfSim after {attempts} attempts.')
                    Event().wait(0.5)
                    continue
                except socket.error as e:
                    msg = f'Socket error when trying to send shot to OpenGolfSim, Exception: {format(e)}'
                    logging.debug(msg)
                    raise SimTCPConnectionSocketError(msg)
                except Exception as e:
                    msg = f"Unknown error when trying to send shot to OpenGolfSim, Exception: {format(e)}"
                    logging.debug(msg)
                    raise SimTCPConnectionUnknownError(msg)
                else:
                    if len(msg) == 0:
                        msg = f"OpenGolfSim closed the connection"
                        logging.debug(msg)
                        raise SimTCPConnectionClientClosedConnection(msg)
                    else:
                        logging.debug(f"Response from OpenGolfSim: {msg}")
                        return msg

    def launch_ball(self, ball_data: BallData) -> None:
        if self._connected:
            device = {
                "shotId": self._shot_number,
                "type": "shot"
            }
            payload = device | ball_data.to_opengolfsim()
            logging.debug(f'Launch Ball payload: {payload} ball_data.to_opengolfsim(): {ball_data.to_opengolfsim()}')
            self.send_msg(json.dumps(payload).encode("utf-8"))
            self._shot_number += 1

    def check_for_message(self):
        message = bytes(0)
        if self._connected:
            read_socket, write_socket, error_socket = select.select([self._socket], [], [], 0)
            while read_socket:
                message = message + self._socket.recv(1024)
                read_socket, write_socket, error_socket = select.select([self._socket], [], [], 0)
        return message

    