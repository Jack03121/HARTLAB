import time
import serial
from serial.tools import list_ports


class SerialManager:
    def __init__(self):
        self.connection = None

    def get_ports(self):
        ports = list_ports.comports()
        return {f"{p.device} - {p.description}": p.device for p in ports}

    def connect(self, port_name):
        self.connection = serial.Serial(
            port=port_name,
            baudrate=1200,
            bytesize=8,
            parity=serial.PARITY_ODD,
            stopbits=1,
            timeout=3
        )

    def disconnect(self):
        if self.connection:
            self.connection.close()

    def transact(self, frame, read_len=64, pause=1.0):
        self.connection.write(frame)
        self.connection.flush()
        time.sleep(pause)
        return self.connection.read(read_len)