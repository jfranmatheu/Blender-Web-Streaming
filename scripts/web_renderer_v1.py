import sys
import os
import socket
import struct
import threading
from PyQt5.QtCore import QUrl, QTimer, Qt, QPoint, QEvent
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QImage, QPainter, QMouseEvent, QKeyEvent
from multiprocessing import shared_memory

class EventServer:
    def __init__(self, host='localhost', port=65432):
        self.host = host
        self.port = port
        self.running = False
        self.sock = None
        self.client_sock = None
        self.thread = None
        
    def start(self, callback):
        """Start server in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self._run_server, args=(callback,))
        self.thread.daemon = True  # Thread will be killed when main process exits
        self.thread.start()
        
    def stop(self):
        """Stop server and close all connections"""
        self.running = False
        if self.client_sock:
            try:
                self.client_sock.shutdown(socket.SHUT_RDWR)
                self.client_sock.close()
            except:
                pass
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except:
                pass
            
    def _run_server(self, callback):
        """Main server loop"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"[SERVER] Listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                self.client_sock, addr = self.sock.accept()
                print(f"[SERVER] Client connected from {addr}")
                self._handle_client(callback)
            except:
                if self.running:  # Only print error if we're still meant to be running
                    print("[SERVER] Connection error, waiting for new client...")
                continue
                
    def _handle_client(self, callback):
        """Handle individual client connection"""
        try:
            while self.running:
                data = self.client_sock.recv(16)  # Expect 16 bytes (4 ints)
                if not data:
                    break
                    
                event_type, x, y, key = struct.unpack('!IiiI', data)
                print(f"[SERVER] Received event: {event_type}, {x}, {y}, {key}")
                callback(event_type, x, y, key)
                
        except Exception as e:
            print(f"[SERVER] Error handling client: {e}")
        finally:
            if self.client_sock:
                self.client_sock.close()
                self.client_sock = None

class OffscreenWebView(QWebEngineView):
    def __init__(self, shared_mem_name):
        super().__init__()
        self.setAttribute(Qt.WA_DontShowOnScreen)
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setFixedSize(1024, 768)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Add page load handler
        self.loadFinished.connect(self.handleLoadFinished)
        
        self.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "custom_page.html")))
        print(f"[QT] Loading page from: {os.path.join(os.path.dirname(__file__), 'custom_page.html')}")

        try:
            self.shared_memory = shared_memory.SharedMemory(create=True, size=1024 * 768 * 4, name=shared_mem_name)
        except FileExistsError:
            self.shared_memory = shared_memory.SharedMemory(name=shared_mem_name)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_page)
        self.timer.start(33)  # Capture every 33ms for ~30FPS

        # Create and start event server
        self.event_server = EventServer()
        self.event_server.start(self.handle_event)

    def handle_event(self, event_type, x, y, key):
        """Handle incoming events from Blender"""
        if not self.hasFocus():
            self.setFocus()

        # Debug JavaScript
        js_debug = f"console.log('Received event: type={event_type}, x={x}, y={y}, key={key}');"
        self.page().runJavaScript(js_debug)

        if event_type == 0:  # Mouse click
            event = QMouseEvent(
                QEvent.MouseButtonPress if key == 0 else QEvent.MouseButtonRelease,
                QPoint(x, y), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
            print(f"[QT] Sending mouse click event: pos={event.pos()}, type={'press' if key == 0 else 'release'}")
            QApplication.sendEvent(self, event)
            # Also inject JavaScript event
            js_click = f"""
            var evt = new MouseEvent('{('mousedown' if key == 0 else 'mouseup')}', {{
                clientX: {x},
                clientY: {y},
                bubbles: true,
                cancelable: true,
                view: window
            }});
            document.elementFromPoint({x}, {y}).dispatchEvent(evt);
            """
            self.page().runJavaScript(js_click)

        elif event_type == 2:  # Mouse move
            event = QMouseEvent(
                QEvent.MouseMove,
                QPoint(x, y),
                Qt.NoButton,  # No buttons pressed
                Qt.NoButton,  # No buttons pressed
                Qt.NoModifier)
            print(f"[QT] Sending mouse move event: pos={event.pos()}")
            QApplication.sendEvent(self, event)
            # Also inject JavaScript event
            js_move = f"""
            var evt = new MouseEvent('mousemove', {{
                clientX: {x},
                clientY: {y},
                bubbles: true,
                cancelable: true,
                view: window
            }});
            document.elementFromPoint({x}, {y}).dispatchEvent(evt);
            """
            self.page().runJavaScript(js_move)

    def event(self, event):
        """Override to debug events"""
        if isinstance(event, QMouseEvent):
            event_type = {
                QEvent.MouseMove: "move",
                QEvent.MouseButtonPress: "press",
                QEvent.MouseButtonRelease: "release"
            }.get(event.type(), str(event.type()))
            print(f"[QT] Mouse event: type={event_type}, pos={event.pos()}, buttons={event.buttons()}")
            # Check if event was accepted
            accepted = super().event(event)
            print(f"[QT] Event was {'accepted' if accepted else 'ignored'}")
            return accepted
        return super().event(event)

    def mousePressEvent(self, event):
        print(f"[QT] mousePressEvent at {event.pos()}")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        print(f"[QT] mouseReleaseEvent at {event.pos()}")
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        print(f"[QT] mouseMoveEvent at {event.pos()}")
        super().mouseMoveEvent(event)

    def handleLoadFinished(self, ok):
        if ok:
            print("[QT] Page loaded successfully")
            # Execute some JavaScript to verify the page is working
            self.page().runJavaScript("document.body.style.backgroundColor", self.handleBackgroundColor)
        else:
            print("[QT] Failed to load page")

    def handleBackgroundColor(self, color):
        print(f"[QT] Page background color: {color}")

    def capture_page(self):
        # print("[QT] Capturing page")
        image = QImage(self.size(), QImage.Format_RGBA8888)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        self.render(painter)
        painter.end()

        # Copy the pixel data directly to shared memory
        byte_data = image.bits().asstring(1024 * 768 * 4)
        self.shared_memory.buf[:len(byte_data)] = byte_data

    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.event_server.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    shared_mem_name = "BWS_SharedMemoryBuffer"
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents)
    view = OffscreenWebView(shared_mem_name)
    view.show()
    sys.exit(app.exec_())