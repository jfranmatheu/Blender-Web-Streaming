from PyQt5.QtCore import QUrl, QMetaObject, Q_ARG, QTimer, Qt, pyqtSlot, QCoreApplication, QEvent, QPoint, QRect
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QMouseEvent, QKeyEvent
import sys
import numpy as np
from time import time
from multiprocessing import shared_memory
import threading
import socket
from string import Template
from PIL import Image


FPS = 30

# Config
URL = "https://twitter.com/Blender"

VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
IMAGE_CHANNELS = 4

SERVER_PORT = 0
SOCKET_CLIENT = None

SHARED_MEMORY_ID = ''
SHM = None
TEXTURE_BUFFER = None

QAPP = None


def main():
    command_line_arguments()
    socket_client = start_socket_client()
    create_app()


def command_line_arguments():
    print(sys.argv)

    if '--' in sys.argv:
        global SHARED_MEMORY_ID
        global SERVER_PORT

        url, whc, SHARED_MEMORY_ID, port = sys.argv[sys.argv.index('--') + 1:]
        width, height, channels = [int(v) for v in whc.split(',')]

        if port and port.isnumeric():
            SERVER_PORT = int(port)
        else:
            print("[bws_pyqt.py] Error: Invalid port argument", port)
            sys.exit(1)
        if url: # .startswith(("https://", "file://")):
            global URL
            URL = url
        else:
            print("[bws_pyqt.py] Error: Invalid url argument", url)
            sys.exit(1)
        if width > 0 and height > 0 and channels in {3, 4}:
            global IMAGE_CHANNELS
            global VIEWPORT_WIDTH
            global VIEWPORT_HEIGHT
            VIEWPORT_WIDTH = width
            VIEWPORT_HEIGHT = height
            IMAGE_CHANNELS = channels
        else:
            print("[bws_pyqt.py] Error: Invalid width and height", width, height)
            sys.exit(1)

        if SHARED_MEMORY_ID != '':
            global SHM
            global TEXTURE_BUFFER
            SHM = shared_memory.SharedMemory(name=SHARED_MEMORY_ID)
            TEXTURE_BUFFER = np.ndarray((VIEWPORT_WIDTH * VIEWPORT_HEIGHT * IMAGE_CHANNELS, ), dtype=np.float32, buffer=SHM.buf)

    elif len(sys.argv) > 1:
        print("[bws_pyqt.py] Error: Expected arguments: url (width height channels) shm server_port")
        sys.exit(1)


def create_app():
    global URL
    global QAPP
    global VIEWPORT_HEIGHT
    global VIEWPORT_WIDTH

    app = QApplication(['-platform', 'minimal'])  # sys.argv)
    QAPP = app
    viewer = Viewer()
    viewer.setFixedSize(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
    viewer.load_url(URL)
    app.exec_()


def start_socket_client():
    global SERVER_PORT
    if not SERVER_PORT:
        print("[bws_pyqt.py] NO SERVER PORT")
        return None

    print("[bws_pyqt.py] Connecting to socket server..")

    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the server socket.gethostname()
    s.connect(('127.0.0.1', SERVER_PORT))
    global SOCKET_CLIENT
    SOCKET_CLIENT = s
    return s


def exit_app():
    print("[bws_pyqt.py] Exit app")
    global SHM
    global TEXTURE_BUFFER
    global SOCKET_CLIENT
    if SOCKET_CLIENT:
        SOCKET_CLIENT.close()
        SOCKET_CLIENT = None
    if SHM:
        SHM.close()
        SHM = None
        TEXTURE_BUFFER = None

    global QAPP
    QAPP.quit()  # exit with success, otherwise use exit()


########################################################################
########################################################################
########################################################################

MOUSEMOVE = Template("""
var x = ${x}; // replace with your x coordinate
var y = ${y}; // replace with your y coordinate
var element = document.elementFromPoint(x, y);
if (element) {
    var mouseMoveEvent = new MouseEvent('mousemove', {
        'view': window,
        'bubbles': true,
        'cancelable': true,
        'screenX': x,
        'screenY': y,
        'clientX': x,
        'clientY': y
    });
    element.dispatchEvent(mouseMoveEvent);
""")

MOUSE_MOVE_JS = """
var lastActiveElement = null;

function mouseMove(x, y) {
    var element = document.elementFromPoint(x, y);
    if (element) {
        var mouseMoveEvent = new MouseEvent('mousemove', {
            'view': window,
            'bubbles': true,
            'cancelable': true,
            'screenX': x,
            'screenY': y,
            'clientX': x,
            'clientY': y
        });
        element.dispatchEvent(mouseMoveEvent);

        // If there was a last active element and it's not the current element, blur it
        if (lastActiveElement && lastActiveElement !== element && typeof lastActiveElement.blur === 'function') {
            lastActiveElement.blur();
        }

        // If the current element can be focused, focus it and set it as the last active element
        if (typeof element.focus === 'function') {
            element.focus();
            lastActiveElement = element;
        }
    }
}
"""

MOUSECLICK = Template("""
var x = ${x}; // replace with your x coordinate
var y = ${y}; // replace with your y coordinate
var element = document.elementFromPoint(x, y);
if (element) element.click();
""")

SCROLL_BY = Template("""
var x = ${deltaX}; // replace with your x coordinate
var y = ${deltaY}; // replace with your y coordinate
window.scrollBy(x, y);
""")

KEYPRESS = Template("""
// var element = document.querySelector('input'); // replace with your element
var element = document.activeElement;
// if (element && element.tagName == 'INPUT') {
//     console.log(element.value);  // print the value of the input field
// }
var event = new KeyboardEvent('keydown', {key: '${key}'}); // replace with your key
if (element) element.dispatchEvent(event);
""")


def mouse_move(view: 'Viewer', page: QWebEnginePage, x: int, y: int):
    print("mouse is moving to:", x, y)
    # create a QMouseEvent
    event = QMouseEvent(QEvent.MouseMove, QPoint(x, y), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    # post the event to the QApplication
    QCoreApplication.postEvent(view, event)
    # page.runJavaScript(MOUSEMOVE.substitute(x=x, y=y))
    # page.runJavaScript(MOUSE_MOVE_JS + f'\nmouseMove({x}, {y});')
    page.runJavaScript(f'mouseMove({x}, {y});')

def mouse_click(page: QWebEnginePage, x: int, y: int):
    page.runJavaScript(MOUSECLICK.substitute(x=x, y=y))

def scroll_by(page: QWebEnginePage, deltaX: int, deltaY: int):
    page.runJavaScript(SCROLL_BY.substitute(deltaX=deltaX, deltaY=deltaY))

def keypress(page: QWebEnginePage, key: str):
    page.runJavaScript(KEYPRESS.substitute(key=key))


def handle_events(view: 'Viewer', page: QWebEnginePage):
    global SOCKET_CLIENT

    print("[bws_pyqt.py] Start::handle_events", SOCKET_CLIENT)

    buffer = ''
    while True:
        if SOCKET_CLIENT is None:
            exit_app()
            break
        try:
            data = SOCKET_CLIENT.recv(100)
        except socket.error as e:
            print(e)
            exit_app()
            break
        if not data:
            continue
        buffer += data.decode()
        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            commands = line.split(',')
            command_id = commands[0]
            # print(command_id, commands)
            if command_id == '@':
                # SPECIAL COMMANDS FROM PARENT PROCESS.
                command_id = commands[1]
                if command_id == 'KILL':
                    exit_app()
                    return None
            elif command_id == 'mousemove':
                x, y = map(int, commands[1:])
                mouse_move(view, page, x=x, y=y)
                view.dirty = True
            elif command_id == 'click':
                x, y = map(int, commands[1:3])
                mouse_click(page, x=x, y=y)
                view.dirty = True
            elif command_id == 'resize':
                width, height = map(int, commands[1:])
            elif command_id == 'scroll':
                x, y, sign = map(int, commands[1:])
                scroll_by(page, deltaX=0, deltaY=sign*10)
                view.dirty = True
            elif command_id == 'unicode':
                key_press, key, modifiers = map(int, commands[1:])
                keypress(page, key=key)
                view.dirty = True
            else:
                continue

        buffer = ''


def refresh_buffer(view: 'Viewer'):
    ## if not view.dirty:
    ##     return
    ## view.dirty = False

    global TEXTURE_BUFFER
    if TEXTURE_BUFFER is None:
        return
    global VIEWPORT_WIDTH
    global VIEWPORT_HEIGHT

    image = view.grab().toImage()
    ptr = image.constBits()
    ptr.setsize(VIEWPORT_WIDTH * VIEWPORT_HEIGHT * 4)

    image = Image.frombytes("RGBA", (VIEWPORT_WIDTH, VIEWPORT_HEIGHT), ptr, "raw") #, "RGBA", 0, 1)
    # image.save(SCREENSHOT_PATH, "PNG")
    # Convert the image to a numpy array
    arr = np.array(image)
    # Convert the numpy array to float32
    arr = arr.astype(np.float32)
    # Normalize the values to be between 0 and 1
    arr /= 255.0
    # Flatten the array
    arr = arr.flatten()

    if TEXTURE_BUFFER is None:
        return
    TEXTURE_BUFFER[:] = arr[:]
    image.close()
    del image
    del arr


class MyPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, sourceID):
        if msg in {'DOM_CHANGE'}:
            refresh_buffer(self.parent())

class Viewer(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super(Viewer, self).__init__(*args, **kwargs)
        self.setPage(MyPage(self))
        ## self.repaintRequested.connect(self.on_repaint_requested)
        self.dirty = True
        self.frame_count = 0
        self.start_time = time()

    @pyqtSlot()
    def refresh_buffer(self):
        # Process a frame...
        self.frame_count += 1

        # print("Refreshing buffer...")  # Implement your actual logic here
        refresh_buffer(self)

        # Calculate FPS every second
        if time() - self.start_time > 1.0:  # one second has passed
            fps = self.frame_count / (time() - self.start_time)
            print(f'[screenshot.py] FPS: {fps}')

            # Reset the frame count and start time
            self.frame_count = 0
            self.start_time = time()

    def safe_refresh_buffer(self):
        QMetaObject.invokeMethod(self, "refresh_buffer", Qt.QueuedConnection)

    def load_url(self, url):
        self.load(QUrl(url))
        self.loadFinished.connect(self.on_load_finished)
        self.show()

    def on_load_finished(self):
        print('[bws_pyqt.py] Load finished')
        self.page().runJavaScript("""
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    console.log('DOM_CHANGE');
                });
            });
            observer.observe(document, { attributes: true, childList: true, characterData: true, subtree: true });
        """)

        self.page().runJavaScript("""
            window.lastHoveredElement = null;

            window.mouseMove = function(x, y) {
                var element = document.elementFromPoint(x, y);
                element.dispatchEvent(mouseEnterEvent);
                if (element) {
                    if (window.lastHoveredElement && window.lastHoveredElement !== element) {
                        var mouseOutEvent = new MouseEvent('mouseout', {
                            'view': window,
                            'bubbles': true,
                            'cancelable': true
                        });
                        window.lastHoveredElement.dispatchEvent(mouseOutEvent);
                    }

                    if (element !== window.lastHoveredElement) {
                        var mouseEnterEvent = new MouseEvent('mouseenter', {
                            'view': window,
                            'bubbles': true,
                            'cancelable': true
                        });
                        element.dispatchEvent(mouseEnterEvent);
                    }

                    var mouseOverEvent = new MouseEvent('mouseover', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true
                    });
                    element.dispatchEvent(mouseOverEvent);

                    var mouseMoveEvent = new MouseEvent('mousemove', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'screenX': x,
                        'screenY': y,
                        'clientX': x,
                        'clientY': y
                    });
                    element.dispatchEvent(mouseMoveEvent);

                    window.lastHoveredElement = element;
                }
            };
        """)

        print("[bws_pyqt.py] Running thread to handle events from Blender...")
        self.thread = threading.Thread(target=handle_events, args=(self, self.page(),), name='b3d_cef_handle_events')
        self.thread.start()

        # Create a QTimer
        self.timer = QTimer(self)
        # Connect the timer's timeout signal to the refresh_buffer slot
        self.timer.timeout.connect(self.refresh_buffer)
        # Start the timer to trigger every 1000 milliseconds (or adjust as needed)
        self.timer.start(int(1/FPS * 1000))

    ## @pyqtSlot(QRect)
    ## def on_repaint_requested(self, rect):
    ##     print("Repaint requested for:", rect)
    ##     # refresh the buffer here if needed
    ##     self.refresh_buffer()


if __name__ == '__main__':
    main()
