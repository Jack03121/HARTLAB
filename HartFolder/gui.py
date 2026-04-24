from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QComboBox,
    QVBoxLayout, QHBoxLayout, QMessageBox, QTextEdit
)
from PyQt5.QtCore import QTimer

from serial_manager import SerialManager
from hart_protocol import HartProtocol

import csv
import os
from datetime import datetime

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class HartGui(QWidget):
    def __init__(self):
        super().__init__()

        self.serial_manager = SerialManager()
        self.hart = HartProtocol()
        self.port_map = {}

        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_primary_variable)

        self.logging_enabled = False
        self.polling_enabled = False
        self.log_file_name = "hart_log.csv"

        self.pv_history = []
        self.max_points = 50
        self.current_unit = ""

        self.setWindowTitle("HART GUI Starter")
        self.setGeometry(200, 200, 1200, 750)

        self.create_widgets()
        self.create_layout()
        self.connect_signals()
        self.refresh_ports()

    def create_widgets(self):
        self.port_label = QLabel("Available COM Ports:")
        self.port_combo = QComboBox()

        self.refresh_button = QPushButton("Refresh Ports")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.device_info_button = QPushButton("Read Device Info")
        self.read_pv_button = QPushButton("Start PV")
        self.stop_pv_button = QPushButton("Stop PV")

        self.start_logging_button = QPushButton("Start Logging")
        self.stop_logging_button = QPushButton("Stop Logging")
        self.clear_graph_button = QPushButton("Clear Graph")

        self.status_label = QLabel("Status: Disconnected")
        self.device_info_label = QLabel("Device Info: No data")
        self.pv_label = QLabel("PV: No data")
        self.polling_status_label = QLabel("Polling: Off")
        self.logging_status_label = QLabel("Logging: Off")

        self.debug_box = QTextEdit()
        self.debug_box.setReadOnly(True)

        self.figure = Figure(figsize=(8, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Live PV Graph")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("PV")
        self.ax.grid(True)

        self.disconnect_button.setEnabled(False)
        self.device_info_button.setEnabled(False)
        self.read_pv_button.setEnabled(False)
        self.stop_pv_button.setEnabled(False)
        self.start_logging_button.setEnabled(False)
        self.stop_logging_button.setEnabled(False)
        self.clear_graph_button.setEnabled(False)

    def create_layout(self):
        layout = QVBoxLayout()

        layout.addWidget(self.port_label)
        layout.addWidget(self.port_combo)

        row1 = QHBoxLayout()
        row1.addWidget(self.refresh_button)
        row1.addWidget(self.connect_button)
        row1.addWidget(self.disconnect_button)

        row2 = QHBoxLayout()
        row2.addWidget(self.device_info_button)
        row2.addWidget(self.read_pv_button)
        row2.addWidget(self.stop_pv_button)

        row3 = QHBoxLayout()
        row3.addWidget(self.start_logging_button)
        row3.addWidget(self.stop_logging_button)
        row3.addWidget(self.clear_graph_button)

        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)

        layout.addWidget(self.status_label)
        layout.addWidget(self.device_info_label)
        layout.addWidget(self.pv_label)
        layout.addWidget(self.polling_status_label)
        layout.addWidget(self.logging_status_label)
        layout.addWidget(self.canvas)
        layout.addWidget(QLabel("Debug Output:"))
        layout.addWidget(self.debug_box)

        self.setLayout(layout)

    def connect_signals(self):
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.connect_port)
        self.disconnect_button.clicked.connect(self.disconnect_port)
        self.device_info_button.clicked.connect(self.read_device_info)
        self.read_pv_button.clicked.connect(self.start_pv)
        self.stop_pv_button.clicked.connect(self.stop_pv)
        self.start_logging_button.clicked.connect(self.start_logging)
        self.stop_logging_button.clicked.connect(self.stop_logging)
        self.clear_graph_button.clicked.connect(self.clear_graph)

    def log(self, msg):
        self.debug_box.append(msg)

    def refresh_ports(self):
        self.port_combo.clear()
        self.port_map = self.serial_manager.get_ports()

        for label in self.port_map:
            self.port_combo.addItem(label)

    def connect_port(self):
        port = self.port_map[self.port_combo.currentText()]
        self.serial_manager.connect(port)

        self.status_label.setText(f"Connected to {port}")
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.device_info_button.setEnabled(True)
        self.read_pv_button.setEnabled(True)
        self.start_logging_button.setEnabled(True)
        self.clear_graph_button.setEnabled(True)

        self.log(f"Connected to {port}")

    def disconnect_port(self):
        self.serial_manager.disconnect()
        self.timer.stop()

        self.polling_enabled = False
        self.logging_enabled = False

        self.status_label.setText("Disconnected")
        self.device_info_label.setText("Device Info: No data")
        self.pv_label.setText("PV: No data")
        self.polling_status_label.setText("Polling: Off")
        self.logging_status_label.setText("Logging: Off")

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.device_info_button.setEnabled(False)
        self.read_pv_button.setEnabled(False)
        self.stop_pv_button.setEnabled(False)
        self.start_logging_button.setEnabled(False)
        self.stop_logging_button.setEnabled(False)
        self.clear_graph_button.setEnabled(False)

    def read_device_info(self):
        frame = self.hart.build_short_command(0)
        response = self.serial_manager.transact(frame)

        parsed = self.hart.parse_device_info_response(response)

        self.device_info_label.setText(f"UID: {parsed['unique_id']}")
        self.log(f"Long Address: {' '.join(f'{b:02X}' for b in parsed['long_address'])}")

    def start_pv(self):
        if not self.hart.long_address:
            QMessageBox.warning(self, "Warning", "Read Device Info first.")
            return

        self.timer.start(2000)
        self.polling_enabled = True
        self.polling_status_label.setText("Polling: On")

        self.read_pv_button.setEnabled(False)
        self.stop_pv_button.setEnabled(True)

        self.log("PV polling started.")

    def stop_pv(self):
        self.timer.stop()
        self.polling_enabled = False
        self.polling_status_label.setText("Polling: Off")

        self.read_pv_button.setEnabled(True)
        self.stop_pv_button.setEnabled(False)

        self.log("PV polling stopped.")

    def poll_primary_variable(self):
        frame = self.hart.build_long_command(3, self.hart.long_address)
        response = self.serial_manager.transact(frame)

        parsed = self.hart.parse_command3_response(response)
        if not parsed:
            return

        unit_map = {
            0x06: "bar",
            0x20: "°C"
        }

        unit = unit_map.get(parsed["unit_code"], "")
        pv = parsed["pv_value"]
        current = parsed["current"]

        self.current_unit = unit
        self.pv_label.setText(f"PV: {pv:.3f} {unit}")
        self.log(f"{pv:.3f} {unit} | {current:.3f} mA")

        self.pv_history.append(pv)
        if len(self.pv_history) > self.max_points:
            self.pv_history.pop(0)

        self.update_graph()

        if self.logging_enabled:
            with open(self.log_file_name, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now(), pv, unit, current])

    def update_graph(self):
        self.ax.clear()
        self.ax.plot(range(1, len(self.pv_history) + 1), self.pv_history)
        self.ax.set_title("Live PV Graph")
        self.ax.set_xlabel("Sample")

        if self.current_unit:
            self.ax.set_ylabel(f"PV ({self.current_unit})")
        else:
            self.ax.set_ylabel("PV")

        self.ax.grid(True)
        self.canvas.draw()

    def clear_graph(self):
        self.pv_history = []
        self.update_graph()
        self.log("Graph cleared.")

    def start_logging(self):
        self.logging_enabled = True
        self.logging_status_label.setText("Logging: On")
        self.start_logging_button.setEnabled(False)
        self.stop_logging_button.setEnabled(True)

        if not os.path.exists(self.log_file_name):
            with open(self.log_file_name, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "PV", "Unit", "Current"])

        self.log("Logging started.")

    def stop_logging(self):
        self.logging_enabled = False
        self.logging_status_label.setText("Logging: Off")
        self.start_logging_button.setEnabled(True)
        self.stop_logging_button.setEnabled(False)

        self.log("Logging stopped.")

    def closeEvent(self, event):
        self.timer.stop()
        self.serial_manager.disconnect()
        event.accept()