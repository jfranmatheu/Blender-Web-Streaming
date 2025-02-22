import sys
import socket
import struct
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtGui import QImage, QPixmap
from multiprocessing import shared_memory

class SimpleUI(QWidget):
    def __init__(self, shared_mem_name):
        super().__init__()
        self.setFixedSize(1024, 768)
        self.label = QLabel(self)
        self.label.setFixedSize(1024, 768)

        self.shared_memory = shared_memory.SharedMemory(name=shared_mem_name)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_image)
        self.timer.start(100)  # Update every 100ms

    def update_image(self):
        buffer_data = self.shared_memory.buf[:1024 * 768 * 4]
        image = QImage(buffer_data, 1024, 768, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(image)
        self.label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        self.send_event(0, event.x(), event.y(), 0)

    def keyPressEvent(self, event):
        self.send_event(1, 0, 0, event.key())

    def send_event(self, event_type, x, y, key):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 65432))
            s.sendall(struct.pack('!IiiI', event_type, x, y, key))

if __name__ == "__main__":
    shared_mem_name = "SharedMemoryBuffer"

    app = QApplication(sys.argv)
    ui = SimpleUI(shared_mem_name)
    ui.show()
    sys.exit(app.exec_())