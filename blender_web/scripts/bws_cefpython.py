"""
Example of using CEF browser in off-screen rendering mode
(windowless) to create a screenshot of a web page. This
example doesn't depend on any third party GUI framework.
This example is discussed in Tutorial in the Off-screen
rendering section.

Before running this script you have to install Pillow image
library (PIL module):

    pip install Pillow

With optionl arguments to this script you can resize viewport
so that screenshot includes whole page with height like 5000px
which would be an equivalent of scrolling down multiple pages.
By default when no arguments are provided will load cefpython
project page on Github with 5000px height.

Usage:
    python CEF
    python CEF https://github.com/cztomczak/cefpython 1024 5000
    python CEF https://www.google.com/ncr 1024 768

Tested configurations:
- CEF Python v57.0+
- Pillow 2.3.0 / 4.1.0

NOTE: There are limits in Chromium on viewport size. For some
      websites with huge viewport size it won't work. In such
      case it is required to reduce viewport size to an usual
      size of a window and perform scrolling programmatically
      using javascript while making a screenshot for each of
      the scrolled region. Then at the end combine all the
      screenshots into one. To force a paint event in OSR
      mode call cef.Invalidate().
"""

from cefpython3 import cefpython_py39 as cef
import numpy as np
import platform
import sys
import socket
from typing import Any
from time import time, sleep
from math import floor
from multiprocessing import shared_memory
import threading
import struct
from queue import Queue
import json


try:
    from PIL import Image, __version__ as PILLOW_VERSION
except ImportError:
    print("[CEF] Error: PIL module not available. To install"
          " type: pip install Pillow")
    sys.exit(1)


DEBUG = False
PING_INTERVAL = 5  # Time between pings
PONG_TIMEOUT = 2  # Time to wait for a pong
FPS = 30

# Config
URL = "https://twitter.com/Blender"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
IMAGE_CHANNELS = 4
SHARED_MEMORY_ID = ''
SERVER_PORT = 0
SOCKET_LOCK = threading.Lock()

SHM = None
TEXTURE_BUFFER = None

# Off-screen-rendering requires setting "windowless_rendering_enabled"
# option.
settings = {
    "windowless_rendering_enabled": True,
    "debug": DEBUG,
    "log_severity": cef.LOGSEVERITY_INFO,
    "log_file": "debug.log",
    "context_menu": {
        "enabled": False,
    },
    "downloads_enabled": False,
    "background_color": 0x00, # fully transparent
    # "unique_request_context_per_browser": True,
    # "remote_debugging_port": 0,
    # "ignore_certificate_errors": True,
    # "auto_zooming": "system_dpi",
    # "locales_dir_path": cef.GetModuleDirectory()+"/locales",
    # "resources_dir_path": cef.GetModuleDirectory(),
    # "browser_subprocess_path": "%s/%s" % (cef.GetModuleDirectory(), "subprocess"),
}
switches = {
    # GPU acceleration is not supported in OSR mode, so must disable
    # it using these Chromium switches (Issue #240 and #463)
    "disable-gpu": "",
    "disable-gpu-compositing": "",
    # Tweaking OSR performance by setting the same Chromium flags
    # as in upstream cefclient (Issue #240).
    "enable-begin-frame-scheduling": "",
    "disable-surfaces": "",  # This is required for PDF ext to work
    # "enable-media-stream": "", # video and/or audio streaming.
    # "proxy-server": "socks5://127.0.0.1:8888", # proxy server?
    # "disable-d3d11": "",
    # "off-screen-rendering-enabled": "",
    # "off-screen-frame-rate": "60",
    # "disable-gpu-vsync": "",
    # "disable-web-security": "",
}
browser_settings = {
    # Tweaking OSR performance (Issue #240)
    "windowless_frame_rate": 30,  # Default frame rate in CEF is 30
    "background_color": 0x00, # fully transparent
    # "file_access_from_file_urls_allowed": True,
    # "universal_access_from_file_urls_allowed": True,
}

class SOCKET_SIGNAL:
    PING = 0
    PONG = 1
    BUFFER_UPDATE = 2
    KILL = 3

    MOUSE_MOVE = 8
    MOUSE_PRESS = 9
    MOUSE_RELEASE = 10
    MOUSE_DRAG_START = 11
    MOUSE_DRAG_END = 12

    SCROLL_UP = 16
    SCROLL_DOWN = 17

    UNICODE = 24
    
    # UI Events
    BUTTON_CLICK = 32
    INPUT_CHANGE = 33


class MOUSE_BUTTON:
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2


class KeyEventFlags:
    EVENTFLAG_NONE = 0
    EVENTFLAG_CAPS_LOCK_ON = 1 << 0
    EVENTFLAG_SHIFT_DOWN = 1 << 1
    EVENTFLAG_CONTROL_DOWN = 1 << 2
    EVENTFLAG_ALT_DOWN = 1 << 3
    EVENTFLAG_LEFT_MOUSE_BUTTON = 1 << 4
    EVENTFLAG_MIDDLE_MOUSE_BUTTON = 1 << 5
    EVENTFLAG_RIGHT_MOUSE_BUTTON = 1 << 6
    # Mac OS-X command key.
    EVENTFLAG_COMMAND_DOWN = 1 << 7
    EVENTFLAG_NUM_LOCK_ON = 1 << 8
    EVENTFLAG_IS_KEY_PAD = 1 << 9
    EVENTFLAG_IS_LEFT = 1 << 10
    EVENTFLAG_IS_RIGHT = 1 << 11


EVENT_DATA_BYTES = {
    SOCKET_SIGNAL.MOUSE_MOVE        : 'II',     # (X, Y)
    SOCKET_SIGNAL.MOUSE_PRESS       : 'III',    # (X, Y, MOUSE_BUTTON)
    SOCKET_SIGNAL.MOUSE_RELEASE     : 'III',    # (X, Y, MOUSE_BUTTON)
    SOCKET_SIGNAL.MOUSE_DRAG_START  : 'II',     # (X, Y)
    SOCKET_SIGNAL.MOUSE_DRAG_END    : 'II',     # (X, Y)
    SOCKET_SIGNAL.SCROLL_UP         : 'II',     # (X, Y)
    SOCKET_SIGNAL.SCROLL_DOWN       : 'II',     # (X, Y)
    SOCKET_SIGNAL.UNICODE           : 'II',     # (UNICODE CODE, KeyEventFlags)
    SOCKET_SIGNAL.BUTTON_CLICK      : 'I',      # (button_id length, button_id string)
    SOCKET_SIGNAL.INPUT_CHANGE      : 'If',     # (input_id length, input_id string, value)
}


##################################################################################################
##################################################################################################
##################################################################################################


class _Browser:
    """ The methods of this object may be called on any thread unless otherwise indicated in the comments.

        Remember to free all browser references when closing app for the browser to shut down cleanly.
        Otherwise data such as cookies or other storage might not be flushed to disk when closing app,
        and other issues might occur as well. To free a reference just assign a None value to a browser variable.

        To compare browser objects always use GetIdentifier() method. Do not compare two Browser objects variables directly."""

    def ExecuteFunction(self, funcName: str, params) -> None:
        """ Call javascript function asynchronously.
            This can also call object's methods, just pass "object.method" as funcName.
            Any valid javascript syntax is allowed as funcName, you could even pass an anonymous function here.

            For a list of allowed types for mixed see JavascriptBindings.IsValueAllowed() (except function, method and instance).

            Passing a python function here is not allowed, it is only possible through JavascriptCallback object. """
        pass

    def ExecuteJavascript(self, jsCode: str, scriptUrl: str = '', startLine: int = 1) -> None:
        """ Execute a string of JavaScript code in this frame.
            The scriptURL parameter is the URL where the script in question can be found, if any.
            The renderer may request this URL to show the developer the source of the error.
            The startLine parameter is the base line number to use for error reporting.

            This function executes asynchronously so there is no way to get the returned value.

            Calling javascript from native code synchronously is not possible in CEF 3.
            It is also not possible doing it synchronously the other way around ie. js->native. """
        pass

    def GetUrl(self) -> str: pass
    def GetUserData(self, key) -> Any: pass
    def GetIdentifier(self) -> int: pass
    def GetZoomLevel(self) -> float: pass
    def GoBack(self) -> None: pass
    def GoForward(self) -> None: pass
    def HasDevTools(self) -> bool: pass
    def HasDocument(self) -> bool: pass
    def IsFullscreen(self) -> bool: pass

    def GetWindowHandle(self) -> object: # return windowHandle
        """ Returns an inner or outer window handle for the browser.
            If the browser was created using CreateBrowserSync() then this will return an inner CEF-internal window handle.
            If this is a popup browser created from javascript using window.open() and
            its WindowInfo has not been set in LifespanHandler.OnAfterCreated(),
            then it returns CEF-internal window handle which is the most outer window handle in this case. """
        pass

    def GetImage(self) -> tuple[bytes, int, int]:
        """ Currently available only on Linux (Issue #427).
            Get browser contents as image. Only screen visible contents are returned.
            Returns an RGB buffer which can be converted to an image using PIL library with Image.frombytes
            (https://github.com/cztomczak/cefpython/blob/master/api/Browser.md#getimage) """
        pass

    def IsLoading(self) -> bool:
        """ Available only in CEF 3. Not yet implemented.
            Returns true if the browser is currently loading. """
        pass

    def LoadUrl(self, url: str) -> None:
        """ Load url in the main frame.
            NOTE: Browser.Navigate() is an alias of LoadUrl.
            If the url is a local path it needs to start with the file:// prefix.
            If the url contains special characters it may need proper handling.
            Starting with v66.1+ it is required for the app code to encode the url properly.
            You can use the pathlib.PurePath.as_uri in Python 3 or urllib.pathname2url in Python 2
            (urllib.request.pathname2url in Python 3) depending on your case. """
        pass

    def Print(self) -> None:
        """ Print the current browser contents. """
        pass

    def Reload(self) -> None:
        """ Reload the current page. """
        pass

    def ReloadIgnoreCache(self) -> None:
        """ Reload the current page ignoring any cached data. """
        pass

    def SendKeyEvent(self, event) -> None:
        """ KeyEvent is a dictionary, see KeyboardHandler.OnPreKeyEvent() for a description of the available keys.
            https://github.com/cztomczak/cefpython/blob/master/api/KeyboardHandler.md """
        pass

    def SendMouseClickEvent(self, x: int, y: int, mouseButtonType: int, mouseUp: bool, clickCount: int, modifiers: int) -> None:
        """ Send a mouse click event to the browser. The |x| and |y| coordinates are relative to the upper-left corner of the view.

            ### mouseButtonType may be one of:
            - cefpython.MOUSEBUTTON_LEFT
            - cefpython.MOUSEBUTTON_MIDDLE
            - cefpython.MOUSEBUTTON_RIGHT

            ### modifiers flags:
            - EVENTFLAG_NONE
            - EVENTFLAG_CAPS_LOCK_ON
            - EVENTFLAG_SHIFT_DOWN
            - EVENTFLAG_CONTROL_DOWN
            - EVENTFLAG_ALT_DOWN
            - EVENTFLAG_LEFT_MOUSE_BUTTON
            - EVENTFLAG_MIDDLE_MOUSE_BUTTON
            - EVENTFLAG_RIGHT_MOUSE_BUTTON
            - EVENTFLAG_COMMAND_DOWN (Mac)
            - EVENTFLAG_NUM_LOCK_ON (Mac)
            - EVENTFLAG_IS_KEY_PAD (Mac)
            - EVENTFLAG_IS_LEFT (Mac)
            - EVENTFLAG_IS_RIGHT (Mac) """
        pass

    def SendMouseMoveEvent(self, x: int, y: int, mouseLeave: bool, modifiers: int) -> None:
        """ Send a mouse move event to the browser.
            The |x| and |y| coordinates are relative to the upper-left corner of the view.
            For a list of modifiers flags see SendMouseClickEvent(). """
        pass

    def SendMouseWheelEvent(self, x: int, y: int, deltaX: int, deltaY: int, modifiers: int = 0) -> None:
        """ Send a mouse wheel event to the browser.
            The |x| and |y| coordinates are relative to the upper-left corner of the view.
            The |deltaX| and |deltaY| values represent the movement delta in the X and Y directions respectively.
            In order to scroll inside select popups with window rendering disabled RenderHandler.GetScreenPoint()
            should be implemented properly. For a list of modifiers flags see SendMouseClickEvent(). """
        pass

    def SendFocusEvent(self, setFocus: bool) -> None:
        """ Send a focus event to the browser. """
        pass

    def SetFocus(self, focus: bool) -> None:
        """ Set whether the browser is focused. """
        pass

    def SetClientCallback(self, name: str, callback: callable) -> None:
        """ Set client callback. """
        pass

    def SetClientHandler(self, clientHandler: object) -> None:
        """ Set client handler object (class instance), its members will be inspected.
            Private methods that are not meant to be callbacks should have their names prepended with an underscore.

            You can call this method multiple times with to set many handlers.
            For example you can create in your code several objects named LoadHandler, LifespanHandler etc. """
        pass

    def SetJavascriptBindings(self, bindings) -> None: # : JavascriptBindings
        """ Set javascript bindings. """
        pass

    def SetUserData(self, key, value) -> None:
        """ Set user data. Use this function to keep data associated with this browser. See also GetUserData(). """
        pass

    def SetZoomLevel(self, zoomLevel: float) -> None:
        """ Change the zoom level to the specified value. Specify 0.0 to reset the zoom level.
            If called on the UI thread the change will be applied immediately.
            Otherwise, the change will be applied asynchronously on the UI thread. """
        pass

    def ShowDevTools(self) -> None:
        """ Open developer tools (DevTools) in its own browser. The DevTools browser will remain associated with this browser.
            If the DevTools browser is already open then it will be focused, in which case the |windowInfo|, |client| and |settings| parameters will be ignored.
            If |inspect_element_at| is non-empty then the element at the specified (x,y) location will be inspected.
            The |windowInfo| parameter will be ignored if this browser is wrapped in a CefBrowserView. """
        pass

    def CloseDevTools(self) -> None:
        """ Explicitly close the associated DevTools browser, if any. """
        pass

    def StartDownload(self, url: str) -> None:
        """ Download the file at |url| using DownloadHandler. """
        pass

    def StopLoad(self) -> None:
        """ Stop loading the page. """
        pass

    def CloseBrowser(self, forceClose: bool) -> None:
        """ Closes the browser. If the window was created explicitily by you (not a popup) you still need to post WM_DESTROY message to the window.

            Request that the browser close. The Javascript 'onbeforeunload' event will be fired.
            If |force_close| is false the event handler, if any, will be allowed to prompt the user and the user can optionally cancel the close.
            If |force_close| is true the prompt will not be displayed and the close will proceed.
            Results in a call to LifespanHandler::DoClose() if the event handler allows the close or if |force_close| is true.
            See LifespanHandler::DoClose() documentation for additional usage information. """
        pass

    def TryCloseBrowser(self) -> None:
        """ Helper for closing a browser. Call this method from the top-level window close handler.
            Internally this calls CloseBrowser(false) if the close has not yet been initiated.
            This method returns false while the close is pending and true after the close has completed.
            See CloseBrowser() and CefLifeSpanHandler::DoClose() documentation for additional usage information.
            This method must be called on the browser process UI thread. """
        pass

    def WasResized(self) -> None:
        """ Notify the browser that the widget has been resized.
            The browser will first call RenderHandler::GetViewRect to get the new size and
            then call RenderHandler::OnPaint asynchronously with the updated regions.
            * This method is only used when window rendering is disabled. * """
        pass

    def WasHidden(self) -> None:
        """ Notify the browser that it has been hidden or shown.
            Layouting and RenderHandler::OnPaint notification will stop when the browser is hidden.
            * This method is only used when window rendering is disabled. * """
        pass


class _PaintBuffer:
    """ This object used in: RenderHandler.OnPaint(). """

    def GetIntPointer(self) -> int:
        """ Get int pointer to the void* buffer.
            |buffer| will be |width|*|height|*4 bytes in size and represents a BGRA image with an upper-left origin. """
        pass

    def GetBytes(self, mode: str = 'bgra', origin: str = 'top-left') -> object:
        ''' Converts the void* buffer to string. In Py2 returns 'str' type, in Py3 returns 'bytes' type.
            ### Parameters:
            - `origin` may be one of: "top-left", "bottom-left".
            - `mode` may be one of: "bgra", "rgba".'''
        pass


class _WindowInfo:
    def SetAsChild(self, parentWindowHandle: int, windowRect: list) -> None:
        """ Create the browser as a child window/view.
            windowRect (optional) example value: [left, top, right, bottom]."""
        pass

    def SetAsPopup(self, parentWidnowHandle: int, windowName: str) -> None:
        """ Available only on Windows. """
        pass

    def SetAsOffscreen(self, parentWindowHandle: int) -> None:
        """ Description from upstream CEF:

            Create the browser using windowless (off-screen) rendering.
            No window will be created for the browser and all rendering will occur via the CefRenderHandler interface.
            The |parent| value will be used to identify monitor info and to act as the parent window for dialogs, context menus, etc.
            If |parent| is not provided then the main screen monitor will be used and some functionality that requires a parent window may not function correctly.
            In order to create windowless browsers the CefSettings.windowless_rendering_enabled value must be set to true.
            Transparent painting is enabled by default but can be disabled by setting CefBrowserSettings.background_color to an opaque value.

            Call this method to disable windowed rendering and to use RenderHandler. See the pysdl2, screenshot, panda3d and kivy examples.
            In order to create windowless browsers the ApplicationSettings.windowless_rendering_enabled value must be set to true.
            You can pass 0 as parentWindowHandle, but then some things like context menus and plugins may not display correctly. """
        pass


class CEF:
    ExceptHook = cef.ExceptHook  # Global except hook to exit app cleanly on error. # To shutdown all CEF processes on error

    @staticmethod
    def CreateBrowserSync(window_info: _WindowInfo = None, settings: dict = None, url: str = '', window_title: str = '') -> _Browser:
        """ All parameters are optional.
            BrowserSettings: https://github.com/cztomczak/cefpython/blob/master/api/BrowserSettings.md """
        return cef.CreateBrowserSync(
            window_info=window_info,
            settings=settings,
            url=url,
            window_title=window_title
        )

    @staticmethod
    def GetAppSetting(key: str) -> object:
        """ Returns ApplicationSettings option that was passed to Initialize(). Returns None if key is not found. """
        return cef.GetAppSetting(key)

    @staticmethod
    def GetAppPath(file: str = None) -> str:
        """ Get path to where application resides. """
        return cef.GetAppPath(file)

    @staticmethod
    def GetBrowserByWindowHandle(windowHandle: int) -> _Browser:
        return cef.GetBrowserByWindowHandle(windowHandle)

    @staticmethod
    def Initialize(settings = None, switches = None) -> bool:
        """ This function should be called on the main application thread (UI thread)
            to initialize CEF when the application is started.
            A call to Initialize() must have a corresponding call to Shutdown() so that CEF exits cleanly.
            Otherwise when application closes data (eg. storage, cookies) might not be saved to disk
            or the process might freeze (experienced on Windows XP). """
        print("Initializing CEF")
        return cef.Initialize(settings=settings, switches=switches)

    @staticmethod
    def SetGlobalClientCallback(name: str, callback: callable) -> None:
        """ Current CEF Python implementation is limited in handling callbacks that occur during browser creation,
            in such cases a callback set with Browser.SetClientCallback() or Browser.SetClientHandler() won't work,
            as this methods can be called only after browser was created. An example of such callback is LifespanHandler.OnAfterCreated().

            Some client callbacks are not associated with any browser.
            In such case use this function instead of the SetClientCallback() and SetClientHandler() Browser methods.
            An example of such callback is OnCertificateError() in RequestHandler.

            Example of using SetGlobalClientCallback() is provided in the wxpython.py example. """
        cef.SetGlobalClientCallback(name, callback)

    @staticmethod
    def SetGlobalClientHandler(handler: object) -> None:
        """ Set client handler object (class instance). Its members will be inspected.
            Private methods that are not meant to be callbacks should have their names prepended with two underscores.
            Methods with single underscore or no underscore are treated the same as client callbacks.

            You can call this method multiple times to set many handlers.
            For example you can create in your code several objects named AccessibilityHandler, RequestHandler etc. """
        cef.SetGlobalClientHandler(handler)

    @staticmethod
    def MessageLoop() -> None:
        """ Run the CEF message loop.
            Use this function instead of an application- provided message loop to get the best balance between performance and CPU usage.
            This function should only be called on the main application thread (UI thread) and only if cefpython.Initialize() is called
            with a ApplicationSettings.multi_threaded_message_loop value of false. This function will block until a quit message is received by the system. """
        cef.MessageLoop()

    @staticmethod
    def MessageLoopWork() -> None:
        """ Call this function in a periodic timer (eg. 10ms).

            Description from upstream CEF:
            Perform a single iteration of CEF message loop processing.
            This function is provided for cases where the CEF message loop must be integrated into an existing application message loop.
            Use of this function is not recommended for most users; use either the CefRunMessageLoop() function or CefSettings.multi_threaded_message_loop if possible.
            When using this function care must be taken to balance performance against excessive CPU usage.
            It is recommended to enable the CefSettings.external_message_pump option when using this function
            so that CefBrowserProcessHandler::OnScheduleMessagePumpWork() callbacks can facilitate the scheduling process.
            This function should only be called on the main application thread and only if CefInitialize()
            is called with a CefSettings.multi_threaded_message_loop value of false. This function will not block. """
        cef.MessageLoopWork()

    @staticmethod
    def QuitMessageLoop() -> None:
        """ Quit the CEF message loop that was started by calling cefpython.MessageLoop().
            This function should only be called on the main application thread (UI thread) and only if cefpython.MessageLoop() was used. """
        cef.QuitMessageLoop()

    @staticmethod
    def PostTask(thread: int, func: object, *args) -> None:
        cef.PostTask(thread, func, *args)

    @staticmethod
    def PostDelayedTask(thread: int, delayed_ms: int, func: object, *args) -> None:
        cef.PostDelayedTask(thread, delayed_ms, func, *args)

    @staticmethod
    def Shutdown() -> None:
        cef.Shutdown()

    @staticmethod
    def WindowInfo() -> _WindowInfo:
        return cef.WindowInfo()



class KeyEventTypes:
  # Notification that a key transitioned from "up" to "down".
  KEYEVENT_RAWKEYDOWN = 0,
  # Notification that a key was pressed. This does not necessarily correspond
  # to a character depending on the key and language. Use KEYEVENT_CHAR for
  # character input.
  KEYEVENT_KEYDOWN = 1
  # Notification that a key was released.
  KEYEVENT_KEYUP = 2
  # Notification that a character was typed. Use this for text input. Key
  # down events may generate 0, 1, or more than one character event depending
  # on the key, locale, and operating system.
  KEYEVENT_CHAR = 3


#############################################################################################
#############################################################################################
#############################################################################################


class QueueUniqueElements:
    def __init__(self) -> None:
        self._ordered_items = Queue()
        self._items_set = set()

    @property
    def qsize(self) -> int:
        return self._ordered_items.qsize()

    def __contains__(self, item) -> bool:
        return item in self._items_set

    def put(self, item, block: bool = True, timeout: float = None) -> None:
        if item not in self._items_set:
            self._ordered_items.put(item, block=block, timeout=timeout)
            self._items_set.add(item)

    def get(self, block: bool = True, timeout: float = None):
        item = self._ordered_items.get(block=block, timeout=timeout)
        self._items_set.remove(item)
        return item


class Client:
    _instance = None

    @classmethod
    def get(cls, create: bool = False) -> 'Client':
        if cls._instance is None:
            if create:
                global SERVER_PORT
                cls._instance = cls('127.0.0.1', SERVER_PORT)
        return cls._instance

    def __init__(self, host, port):
        print("[CLIENT] Create client")
        self.host = host
        self.port = port
        self.connected = False

        self.is_dragging = False

    def tcp_echo_client(self):
        ## self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ## # self.sock.setblocking(False)
        ## self.sock.connect((self.host, self.port))
        ## print("[CLIENT] Connected to", self.host, self.port)

        # Comienza dos hilos, uno para leer y otro para escribir
        import threading
        self.read_thread = threading.Thread(target=self.read_data, daemon=True)
        self.read_thread.start()

    def read_data(self):
        while BrowserWrapper.get() is None:
            sleep(0.1)
        global SERVER_PORT
        # https://realpython.com/python-sockets/
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            self.sock = s
            # s.settimeout(1.0)
            print("[CLIENT] Connected to", self.host, self.port)
            while self.sock is not None:
                if BrowserWrapper._instance is None:
                    break
                try:
                    signal_raw = s.recv(4)
                    if not signal_raw:
                        sleep(1/FPS)
                        continue
                except BlockingIOError:
                    # Resource temporarily unavailable (errno EWOULDBLOCK)
                    sleep(1/FPS)
                    continue
                except socket.error as e:
                    self.sock = None
                    # print("[CLIENT] Some socket error! Closing client and app! BYE BYE!", e)
                    continue

                signal = int.from_bytes(signal_raw, byteorder='big')
                print("[CLIENT] Received signal:", signal)

                if signal == SOCKET_SIGNAL.PONG:
                    if not self.pong_expected:
                        print("[CLIENT] WTF? Not expected pong received!")
                    self.pong_expected = False
                    continue

                if signal == SOCKET_SIGNAL.KILL:
                    exit_app()
                    return None

                event_data_bytes = EVENT_DATA_BYTES.get(signal, None)
                if event_data_bytes is None:
                    raise ValueError("[CLIENT] Unknown event signal was received!", signal)

                # self.sock.settimeout(0.1)
                event_data_raw = s.recv(struct.calcsize(event_data_bytes))
                # self.sock.settimeout(None)
                if not event_data_raw:
                    print("[CLIENT] WARN! Received empty event data!", signal)
                    # sleep(0.1)
                    continue

                event_data = struct.unpack(event_data_bytes, event_data_raw)
                print("[CLIENT] Received event data:", event_data)

                if signal == SOCKET_SIGNAL.MOUSE_MOVE:
                    if self.is_dragging:
                        # x0, y0 = self.drag_prev_mouse
                        # x1, y1 = event_data
                        # diff_x = abs(x1 - x0)
                        # steps = floor(diff_x / 10)
                        # if steps > 0:
                        #     sign = 1 if x1 > x0 else -1
                        #     off_x = x1 + 10 * sign
                        #     for step_index in range(steps):
                        #         BrowserWrapper.get().browser.SendMouseMoveEvent(off_x, self.drag_init_mouse[1], mouseLeave=False)
                        #         off_x += (10 * sign)
                        # self.drag_prev_mouse = event_data
                        event_data = (event_data[0], self.drag_init_mouse[1])
                    BrowserWrapper.get().browser.SendMouseMoveEvent(*event_data, mouseLeave=False)

                elif signal in {SOCKET_SIGNAL.MOUSE_PRESS, SOCKET_SIGNAL.MOUSE_RELEASE}:
                    x, y, _mouse_type = event_data
                    if _mouse_type == MOUSE_BUTTON.LEFT:
                        mouse_type = 'MOUSEBUTTON_LEFT'
                    elif _mouse_type == MOUSE_BUTTON.RIGHT:
                        mouse_type = 'MOUSEBUTTON_RIGHT'
                    elif _mouse_type == MOUSE_BUTTON.MIDDLE:
                        mouse_type = 'MOUSEBUTTON_MIDDLE'
                    else:
                        raise ValueError("[CLIENT] Unexpected mouse type value!", _mouse_type)

                    mouse_up = signal == SOCKET_SIGNAL.MOUSE_RELEASE
                    BrowserWrapper.get().browser.SendMouseClickEvent(x=x, y=y, mouseButtonType=getattr(cef, mouse_type), mouseUp=mouse_up, clickCount=1)

                elif signal in {SOCKET_SIGNAL.SCROLL_UP, SOCKET_SIGNAL.SCROLL_DOWN}:
                    sign = 1 if signal == SOCKET_SIGNAL.SCROLL_DOWN else -1
                    BrowserWrapper.get().browser.SendMouseWheelEvent(*event_data, deltaX=0, deltaY=sign*10)

                elif signal in {SOCKET_SIGNAL.MOUSE_DRAG_START, SOCKET_SIGNAL.MOUSE_DRAG_END}:
                    self.is_dragging = signal == SOCKET_SIGNAL.MOUSE_DRAG_START
                    # if self.is_dragging:
                    #     BrowserWrapper.get().get_element_at_mouse_position(*event_data)
                    self.drag_prev_mouse = event_data
                    self.drag_init_mouse = event_data
                    BrowserWrapper.get().browser.SendMouseClickEvent(*event_data, mouseButtonType=cef.MOUSEBUTTON_LEFT, mouseUp=(not self.is_dragging), clickCount=1)

                elif signal == SOCKET_SIGNAL.UNICODE:
                    char_code, flags = event_data
                    key_event = {
                        'type': KeyEventTypes.KEYEVENT_CHAR,  # KeyEventTypes.KEYEVENT_KEYDOWN if key_press==1 else KeyEventTypes.KEYEVENT_KEYUP,
                        'windows_key_code': char_code,  # windows_vk_code
                        'character': char_code,
                        'focus_on_editable_field': True,
                        'is_system_key': False,
                        'modifiers': flags
                    }
                    BrowserWrapper.get().browser.SendKeyEvent(key_event)

        exit_app()


def main():
    check_versions()
    sys.excepthook = CEF.ExceptHook  # To shutdown all CEF processes on error

    command_line_arguments()
    CEF.Initialize(settings=settings, switches=switches)
    BrowserWrapper.get()
    Client.get(create=True).tcp_echo_client()
    CEF.MessageLoop()
    CEF.Shutdown()


def check_versions():
    ver = cef.GetVersion()
    print("[cefpython] CEF Python {ver}".format(ver=ver["version"]))
    print("[cefpython] Chromium {ver}".format(ver=ver["chrome_version"]))
    print("[cefpython] CEF {ver}".format(ver=ver["cef_version"]))
    print("[cefpython] Python {ver} {arch}".format(
           ver=platform.python_version(),
           arch=platform.architecture()[0]))
    print("[cefpython] Pillow {ver}".format(ver=PILLOW_VERSION))
    assert cef.__version__ >= "57.0", "CEF Python v57.0+ required to run this"


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
            print("[CEF] Error: Invalid port argument", port)
            sys.exit(1)
        if url.startswith(("https://", "file://")):
            global URL
            URL = url
        else:
            print("[CEF] Error: Invalid url argument", url)
            sys.exit(1)
        if width > 0 and height > 0 and channels in {3, 4}:
            global IMAGE_CHANNELS
            global VIEWPORT_WIDTH
            global VIEWPORT_HEIGHT
            VIEWPORT_WIDTH = width
            VIEWPORT_HEIGHT = height
            IMAGE_CHANNELS = channels
        else:
            print("[CEF] Error: Invalid width and height", width, height)
            sys.exit(1)

        if SHARED_MEMORY_ID != '':
            global SHM
            global TEXTURE_BUFFER
            SHM = shared_memory.SharedMemory(name=SHARED_MEMORY_ID)
            TEXTURE_BUFFER = np.ndarray((VIEWPORT_WIDTH * VIEWPORT_HEIGHT * IMAGE_CHANNELS, ), dtype=np.float32, buffer=SHM.buf)

    elif len(sys.argv) > 1:
        print("[CEF] Error: Expected arguments: url (width height channels) shm server_port")
        sys.exit(1)


def exit_app():
    # Important note:
    #   Do not close browser nor exit app from OnLoadingStateChange
    #   OnLoadError or OnPaint events. Closing browser during these
    #   events may result in unexpected behavior. Use cef.PostTask
    #   function to call exit_app from these events.
    print("[CEF] Close browser and exit app")
    global SHM
    global TEXTURE_BUFFER
    if client := Client._instance:
        Client._instance = None
        client.sock = None
        del client
    if SHM:
        SHM.close()
        SHM = None
        TEXTURE_BUFFER = None
    BrowserWrapper.get().close()



class BrowserWrapper:
    _instance: 'BrowserWrapper' = None

    @classmethod
    def get(cls) -> 'BrowserWrapper':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        global VIEWPORT_HEIGHT
        global VIEWPORT_WIDTH
        # Create browser in off-screen-rendering mode (windowless mode)
        # by calling SetAsOffscreen method. In such mode parent window
        # handle can be NULL (0).
        parent_window_handle = 0
        window_info = CEF.WindowInfo()
        window_info.SetAsOffscreen(parent_window_handle)
        print(f"[CEF] Viewport size: {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}")
        print("[CEF] Loading url: {url}"
            .format(url=URL))
        browser: _Browser = CEF.CreateBrowserSync(window_info=window_info,
                                        settings=browser_settings,
                                        url=URL,
                                        window_title="OFFSCREEN")
        browser.SetClientHandler(LoadHandler())
        browser.SetClientHandler(RenderHandler())
        browser.SetClientHandler(JSQueryHandler())
        browser.SendFocusEvent(True)
        # You must call WasResized at least once to let know CEF that
        # viewport size is available and that OnPaint may be called.
        browser.WasResized()
        self.browser = browser

    def get_element_at_mouse_position(self, x, y):
        if self.browser is None:
            return
        
        def _print_element(self, html):
            # Print HTML of the element at mouse position
            print(html)
        # Execute JavaScript to find the element at mouse position
        script = f"""
            var element = document.elementFromPoint({x}, {y});
            element.outerHTML;
        """
        self.browser.ExecuteJavascript(script, callback=_print_element)

    def close(self):
        if self.browser:
            self.browser.CloseBrowser()
            self.browser = None
        BrowserWrapper._instance = None
        CEF.QuitMessageLoop()
        CEF.Shutdown()


class LoadHandler(object):
    thread: threading.Thread

    def __init__(self) -> None:
        self.thread = None

    ## def OnLoadingStateChange(self, browser, is_loading, **_):
    ##     """Called when the loading state has changed."""
    ##     if not is_loading:
    ##         print("[CEF] OnLoadingStateChange -> Load Complete!")
    ##         if self.thread is None or not self.thread.is_alive():
    ##             print("[CEF] Running thread to handle events from Blender...")
    ##             self.thread = threading.Thread(target=receive_events, args=(browser,), name='b3d_cef_handle_events', daemon=True)
    ##             self.thread.start()

    def OnLoadError(self, browser: _Browser, frame, error_code, failed_url, **_):
        """Called when the resource load for a navigation fails
        or is canceled."""
        if not frame.IsMain():
            # We are interested only in loading main url.
            # Ignore any errors during loading of other frames.
            return
        print("[CEF] ERROR: Failed to load url: {url}"
              .format(url=failed_url))
        print("[CEF] Error code: {code}"
              .format(code=error_code))
        # See comments in exit_app() why PostTask must be used
        CEF.PostTask(cef.TID_UI, exit_app, browser)


class RenderHandler(object):
    def __init__(self):
        self.OnPaint_called = False
        self.frame_count = 0
        self.start_time = time()

    def GetViewRect(self, rect_out: list, **_) -> bool:
        """Called to retrieve the view rectangle which is relative
        to screen coordinates. Return True if the rectangle was
        provided."""
        # rect_out --> [x, y, width, height]
        rect_out.extend([0, 0, VIEWPORT_WIDTH, VIEWPORT_HEIGHT])
        return True

    def OnPaint(self, browser: _Browser, element_type, paint_buffer: _PaintBuffer, **_) -> None:
        """Called when an element should be painted."""
        global SHM
        if SHM is None:
            print("Can't paint! SHM is not available!")
            return
        if TEXTURE_BUFFER[-1] != 0:
            return

        ## client = Client.get()
        ## if client is None or client.sock is None:
        ##     return

        # Process a frame...
        self.frame_count += 1

        if self.OnPaint_called:
            sys.stdout.write(".")
            sys.stdout.flush()
        else:
            sys.stdout.write("[CEF] OnPaint")
            self.OnPaint_called = True

        if element_type == cef.PET_VIEW:
            # Buffer string is a huge string, so for performance
            # reasons it would be better not to copy this string.

            image = Image.frombytes("RGBA", (VIEWPORT_WIDTH, VIEWPORT_HEIGHT), paint_buffer.GetBytes(mode="rgba", origin="top-left"), "raw", "RGBA", 0, 1)
            # Convert the image to a numpy array
            arr = np.array(image)
            # Convert the numpy array to float32
            arr = arr.astype(np.float32)
            # Normalize the values to be between 0 and 1
            arr /= 255.0
            # Flatten the array
            arr = arr.flatten()

            TEXTURE_BUFFER[:] = arr[:]
            image.close()
            del image
            del arr

            # client.sock.settimeout(0.2)
            ## if client.sock:
            ##     client.sock.sendall(SOCKET_SIGNAL.BUFFER_UPDATE.to_bytes(4, byteorder='big'))
            # client.sock.settimeout(None)
            TEXTURE_BUFFER[-1] = 1
        else:
            raise Exception("Unsupported element_type in OnPaint")

        # Calculate FPS every second
        if time() - self.start_time > 1.0:  # one second has passed
            fps = self.frame_count / (time() - self.start_time)
            print(f'[CEF] FPS: {fps}')

            # Reset the frame count and start time
            self.frame_count = 0
            self.start_time = time()

'''
class JSQueryHandler:
    def OnJSQuery(self, browser, frame, query_id, request, persistent, callback):
        """Handle JavaScript queries from the web page"""
        try:
            data = json.loads(request)
            event_type = data['type']
            
            if event_type == 'button_click':
                button_id = data['id']
                # Send button click event to Blender
                button_id_bytes = button_id.encode('utf-8')
                client = Client.get()
                client.sock.send(SOCKET_SIGNAL.BUTTON_CLICK.to_bytes(4, byteorder='big'))
                client.sock.send(len(button_id_bytes).to_by<tes(4, byteorder='big'))
                client.sock.send(button_id_bytes)

            elif event_type == 'input_change':
                input_id = data['id']
                value = data['value']
                input_type = data['input_type']
                
                # Send input change event to Blender
                input_id_bytes = input_id.encode('utf-8')
                client = Client.get()
                client.sock.send(SOCKET_SIGNAL.INPUT_CHANGE.to_bytes(4, byteorder='big'))
                client.sock.send(len(input_id_bytes).to_bytes(4, byteorder='big'))
                client.sock.send(input_id_bytes)
                client.sock.send(struct.pack('f', float(value)))

            callback.Success("")
            
        except Exception as e:
            print(f"Error handling JavaScript query: {e}")
            callback.Failure(0, str(e))
'''

if __name__ == '__main__':
    main()
