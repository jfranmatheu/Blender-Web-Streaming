import sys
import os
import socket
import struct
import threading
from PyQt5.QtCore import QUrl, QTimer, Qt, QPoint, QEvent, pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QImage, QPainter, QMouseEvent, QKeyEvent, QWheelEvent
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

class EventBridge(QObject):
    """Bridge to handle events between server thread and Qt main thread"""
    eventReceived = pyqtSignal(int, int, int, int)  # type, x, y, key

class MainWindow(QMainWindow):
    def __init__(self, shared_mem_name):
        super().__init__()
        self.setAttribute(Qt.WA_DontShowOnScreen)
        self.setFixedSize(1024, 768)
        
        # Create event bridge
        self.event_bridge = EventBridge()
        self.event_bridge.eventReceived.connect(self.handle_event_main_thread)
        
        # Create web view
        self.web_view = QWebEngineView()
        # Configure web engine settings
        settings = self.web_view.settings()
        # Show scrollbars
        settings.setAttribute(settings.ShowScrollBars, True)
        # Disable popup windows and other features that might interfere
        settings.setAttribute(settings.JavascriptCanOpenWindows, False)
        settings.setAttribute(settings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(settings.FocusOnNavigationEnabled, False)
        # ---
        settings.setAttribute(settings.AllowWindowActivationFromJavaScript, False)
        settings.setAttribute(settings.PlaybackRequiresUserGesture, False)
        # Enable JavaScript
        settings.setAttribute(settings.JavascriptEnabled, True)
        
        # Create a custom page to handle popups
        page = self.web_view.page()
        page.setBackgroundColor(Qt.transparent)
        # Prevent new windows from opening
        page.windowCloseRequested.connect(lambda: None)
        page.profile().setHttpCacheType(page.profile().MemoryHttpCache)
        
        self.web_view.setFixedSize(1024, 768)
        self.web_view.setMouseTracking(True)
        self.web_view.setFocusPolicy(Qt.StrongFocus)
        self.setCentralWidget(self.web_view)
        
        # Load page
        self.web_view.loadFinished.connect(self.handleLoadFinished)
        self.web_view.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(__file__), "custom_page.html")))
        print(f"[QT] Loading page from: {os.path.join(os.path.dirname(__file__), 'custom_page.html')}")

        # Wait for the render widget to be created
        self.web_view.loadFinished.connect(self._setup_render_widget)

        # Setup shared memory
        try:
            self.shared_memory = shared_memory.SharedMemory(create=True, size=1024 * 768 * 4, name=shared_mem_name)
        except FileExistsError:
            self.shared_memory = shared_memory.SharedMemory(name=shared_mem_name)

        # Setup timer for page capture
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture_page)
        self.timer.start(33)

        # Setup event server
        self.event_server = EventServer()
        self.event_server.start(self.event_bridge.eventReceived.emit)

    def _setup_render_widget(self, ok):
        """Setup render widget after page loads"""
        if ok:
            # Get the render widget (focusProxy)
            self.render_widget = self.web_view.focusProxy()
            if self.render_widget:
                print(f"[QT] Render widget found: {self.render_widget.metaObject().className()}")
            else:
                print("[QT] Warning: No render widget found!")

    def handle_event(self, event_type, x, y, key):
        """Deprecated - use handle_event_main_thread instead"""
        pass

    def handle_event_main_thread(self, event_type, x, y, key):
        """Handle incoming events from Blender in the main Qt thread"""
        try:
            if not self.render_widget:
                print("[QT] No render widget available")
                return

            # Get modifier state from key parameter (packed in binary format)
            shift = bool(key & (1 << 24))
            ctrl = bool(key & (1 << 25)) 
            alt = bool(key & (1 << 26))
            oskey = bool(key & (1 << 27))
            
            # Create Qt modifiers flag
            modifiers = Qt.NoModifier
            if shift: modifiers |= Qt.ShiftModifier
            if ctrl: modifiers |= Qt.ControlModifier
            if alt: modifiers |= Qt.AltModifier
            if oskey: modifiers |= Qt.MetaModifier

            if event_type == 0:  # Mouse click
                print(f"[QT] Mouse click: pos=({x}, {y}), press={key==0}, mods={modifiers}")
                event = QMouseEvent(
                    QEvent.MouseButtonPress if key == 0 else QEvent.MouseButtonRelease,
                    QPoint(x, y),
                    Qt.LeftButton,
                    Qt.LeftButton,
                    modifiers
                )
                QApplication.sendEvent(self.render_widget, event)

            elif event_type == 1:  # Mouse wheel
                print(f"[QT] Mouse wheel: delta={key}, pos=({x}, {y})")
                event = QWheelEvent(
                    QPoint(x, y),
                    key * 120,  # Convert to Qt delta (120 units per step)
                    Qt.NoButton,
                    modifiers,
                    Qt.Vertical
                )
                QApplication.sendEvent(self.render_widget, event)

            elif event_type == 2:  # Mouse move
                event = QMouseEvent(
                    QEvent.MouseMove,
                    QPoint(x, y),
                    Qt.NoButton,
                    Qt.NoButton,
                    modifiers
                )
                QApplication.sendEvent(self.render_widget, event)

            elif event_type == 3:  # Unicode keyboard input
                # Key is the unicode value
                print(f"[QT] Unicode key: {chr(key)}, mods={modifiers}")
                event = QKeyEvent(
                    QEvent.KeyPress,
                    0,  # Native key code (not needed for unicode)
                    modifiers,
                    chr(key)
                )
                QApplication.sendEvent(self.render_widget, event)

            elif event_type == 4:  # Special keys
                # Map Blender special keys to Qt key codes
                key_map = {
                    'DEL': Qt.Key_Delete,
                    'RET': Qt.Key_Return,
                    'SPACE': Qt.Key_Space,
                    'BACK_SPACE': Qt.Key_Backspace,
                    'LEFT_ARROW': Qt.Key_Left,
                    'RIGHT_ARROW': Qt.Key_Right,
                    'UP_ARROW': Qt.Key_Up,
                    'DOWN_ARROW': Qt.Key_Down,
                    'TAB': Qt.Key_Tab,
                    'ESC': Qt.Key_Escape,
                }
                
                # Key parameter contains the special key index
                blender_key = list(key_map.keys())[key]
                qt_key = key_map[blender_key]
                
                print(f"[QT] Special key: {blender_key}, mods={modifiers}")
                event = QKeyEvent(
                    QEvent.KeyPress,
                    qt_key,
                    modifiers
                )
                QApplication.sendEvent(self.render_widget, event)
                
                # Send key release after a short delay
                QTimer.singleShot(50, lambda: QApplication.sendEvent(
                    self.render_widget,
                    QKeyEvent(QEvent.KeyRelease, qt_key, modifiers)
                ))

        except Exception as e:
            print(f"[QT] Error handling event: {e}")

    def handleLoadFinished(self, ok):
        if ok:
            print("[QT] Page loaded successfully")
            self.web_view.page().runJavaScript("document.body.style.backgroundColor", 
                lambda color: print(f"[QT] Page background color: {color}"))
            # Add debug logging for events
            js_debug = """
            document.addEventListener('mousemove', function(e) {
                console.log('JS mousemove:', e.clientX, e.clientY);
            }, true);
            document.addEventListener('mousedown', function(e) {
                console.log('JS mousedown:', e.clientX, e.clientY);
            }, true);
            document.addEventListener('mouseup', function(e) {
                console.log('JS mouseup:', e.clientX, e.clientY);
            }, true);
            document.addEventListener('click', function(e) {
                console.log('JS click:', e.clientX, e.clientY);
            }, true);
            """
            self.web_view.page().runJavaScript(js_debug)
        else:
            print("[QT] Failed to load page")

    def capture_page(self):
        image = QImage(self.size(), QImage.Format_RGBA8888)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        self.web_view.render(painter)
        painter.end()

        byte_data = image.bits().asstring(1024 * 768 * 4)
        self.shared_memory.buf[:len(byte_data)] = byte_data

    def closeEvent(self, event):
        """Prevent window from closing"""
        event.ignore()

if __name__ == "__main__":
    # Create QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_SynthesizeMouseForUnhandledTouchEvents)
    app.setQuitOnLastWindowClosed(False)

    # Create main window
    window = MainWindow("BWS_SharedMemoryBuffer")
    window.show()
    
    # Keep strong reference
    app._window = window
    
    # Create event loop
    from PyQt5.QtCore import QEventLoop
    loop = QEventLoop()
    
    # Handle cleanup
    def cleanup():
        print("[QT] Cleaning up...")
        window.event_server.stop()
        window.shared_memory.close()
        app.quit()
    
    # Handle interrupts
    import signal
    signal.signal(signal.SIGINT, lambda *args: cleanup())
    
    try:
        sys.exit(app.exec_())
    except Exception as e:
        print(f"[QT] Error in main loop: {e}")
        cleanup()