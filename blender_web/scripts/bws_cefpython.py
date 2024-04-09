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
    python screenshot.py
    python screenshot.py https://github.com/cztomczak/cefpython 1024 5000
    python screenshot.py https://www.google.com/ncr 1024 768

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
import os
import subprocess
from typing import Any
from time import time
from multiprocessing import shared_memory
import threading
import socket

try:
    from PIL import Image, __version__ as PILLOW_VERSION
except ImportError:
    print("[screenshot.py] Error: PIL module not available. To install"
          " type: pip install Pillow")
    sys.exit(1)


# Config
URL = "https://twitter.com/Blender" # "https://github.com/cztomczak/cefpython"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
IMAGE_CHANNELS = 4
SCREENSHOT_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "screenshot.png")
SHARED_MEMORY_ID = ''
SERVER_PORT = 0
SOCKET_CLIENT = None

SHM = None
TEXTURE_BUFFER = None


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


def main():
    check_versions()
    sys.excepthook = CEF.ExceptHook  # To shutdown all CEF processes on error

    if os.path.exists(SCREENSHOT_PATH):
        print("[screenshot.py] Remove old screenshot")
        os.remove(SCREENSHOT_PATH)

    command_line_arguments()

    socket_client = start_socket_client()

    # Off-screen-rendering requires setting "windowless_rendering_enabled"
    # option.
    settings = {
        "windowless_rendering_enabled": True,
        "debug": True,
        "log_severity": cef.LOGSEVERITY_INFO,
        "log_file": "debug.log",
        "context_menu": {
            "enabled": False,
        },
        # "unique_request_context_per_browser": True,
        # "remote_debugging_port": 0,
        # "downloads_enabled": False,
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
        # "file_access_from_file_urls_allowed": True,
        # "universal_access_from_file_urls_allowed": True,
    }
    CEF.Initialize(settings=settings, switches=switches)
    create_browser(browser_settings)
    CEF.MessageLoop()
    CEF.Shutdown()
    print("[screenshot.py] Opening screenshot with default application")
    open_screenshot_with_default_application(SCREENSHOT_PATH)


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
            print("[screenshot.py] Error: Invalid port argument", port)
            sys.exit(1)
        if url.startswith(("https://", "file://")):
            global URL
            URL = url
        else:
            print("[screenshot.py] Error: Invalid url argument", url)
            sys.exit(1)
        if width > 0 and height > 0 and channels in {3, 4}:
            global IMAGE_CHANNELS
            global VIEWPORT_WIDTH
            global VIEWPORT_HEIGHT
            VIEWPORT_WIDTH = width
            VIEWPORT_HEIGHT = height
            IMAGE_CHANNELS = channels
        else:
            print("[screenshot.py] Error: Invalid width and height", width, height)
            sys.exit(1)

        if SHARED_MEMORY_ID != '':
            global SHM
            global TEXTURE_BUFFER
            SHM = shared_memory.SharedMemory(name=SHARED_MEMORY_ID)
            TEXTURE_BUFFER = np.ndarray((VIEWPORT_WIDTH * VIEWPORT_HEIGHT * IMAGE_CHANNELS, ), dtype=np.float32, buffer=SHM.buf)

    elif len(sys.argv) > 1:
        print("[screenshot.py] Error: Expected arguments: url (width height channels) shm server_port")
        sys.exit(1)


def start_socket_client():
    global SERVER_PORT
    if not SERVER_PORT:
        return None

    print("[screenshot.py] Connecting to socket server..")

    # Create a socket object
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect to the server socket.gethostname()
    s.connect(('127.0.0.1', SERVER_PORT))
    global SOCKET_CLIENT
    SOCKET_CLIENT = s
    return s


def exit_app(browser: _Browser):
    # Important note:
    #   Do not close browser nor exit app from OnLoadingStateChange
    #   OnLoadError or OnPaint events. Closing browser during these
    #   events may result in unexpected behavior. Use cef.PostTask
    #   function to call exit_app from these events.
    print("[screenshot.py] Close browser and exit app")
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
    browser.CloseBrowser()
    CEF.QuitMessageLoop()


def open_screenshot_with_default_application(path):
    if not os.path.exists(path):
        return
    if sys.platform.startswith("darwin"):
        subprocess.call(("open", path))
    elif os.name == "nt":
        # noinspection PyUnresolvedReferences
        os.startfile(path)
    elif os.name == "posix":
        subprocess.call(("xdg-open", path))


def create_browser(settings: dict):
    global VIEWPORT_WIDTH, VIEWPORT_HEIGHT

    # Create browser in off-screen-rendering mode (windowless mode)
    # by calling SetAsOffscreen method. In such mode parent window
    # handle can be NULL (0).
    parent_window_handle = 0
    window_info = CEF.WindowInfo()
    window_info.SetAsOffscreen(parent_window_handle)
    # window_info.SetTransparentPainting(True)
    print(f"[screenshot.py] Viewport size: {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}")
    print("[screenshot.py] Loading url: {url}"
          .format(url=URL))
    browser: _Browser = CEF.CreateBrowserSync(window_info=window_info,
                                    settings=settings,
                                    url=URL,
                                    window_title="OFFSCREEN")
    browser.SetClientHandler(LoadHandler())
    browser.SetClientHandler(RenderHandler())
    browser.SetClientHandler(KeyboardHandler())
    browser.SendFocusEvent(True)
    # You must call WasResized at least once to let know CEF that
    # viewport size is available and that OnPaint may be called.
    browser.WasResized()


def handle_events(browser: _Browser):
    global SOCKET_CLIENT

    print("[screenshot.py] Start::handle_events", SOCKET_CLIENT)

    buffer = ''
    while True:
        if SOCKET_CLIENT is None:
            exit_app(browser)
            break
        try:
            data = SOCKET_CLIENT.recv(100)
        except socket.error as e:
            print(e)
            exit_app(browser)
            break
        if not data:
            continue
        buffer += data.decode()
        while '\n' in buffer:
            line, buffer = buffer.split('\n', 1)
            commands = line.split(',')
            command_id = commands[0]
            print(command_id, commands)
            if command_id == '@':
                # SPECIAL COMMANDS FROM PARENT PROCESS.
                command_id = commands[1]
                if command_id == 'KILL':
                    exit_app(browser)
                    return None
            elif command_id == 'mousemove':
                x, y = map(int, commands[1:])
                browser.SendMouseMoveEvent(x=x, y=y, mouseLeave=False)
            elif command_id == 'click':
                x, y, mouse_up = map(int, commands[1:-1])
                mouseButtonType = getattr(cef, f"MOUSEBUTTON_{commands[-1].upper()}")
                browser.SendMouseClickEvent(x=x, y=y, mouseButtonType=mouseButtonType, mouseUp=bool(mouse_up), clickCount=1)
            elif command_id == 'resize':
                width, height = map(int, commands[1:])
            elif command_id == 'scroll':
                x, y, sign = map(int, commands[1:])
                browser.SendMouseWheelEvent(x=x, y=y, deltaX=0, deltaY=sign*10)
            elif command_id == 'unicode':
                key_press, char, windows_vk_code, modifiers = map(int, commands[1:])
                browser.SendKeyEvent({
                    'type': KeyEventTypes.KEYEVENT_CHAR,  # KeyEventTypes.KEYEVENT_KEYDOWN if key_press==1 else KeyEventTypes.KEYEVENT_KEYUP,
                    'windows_key_code': char,  # windows_vk_code
                    'character': char,
                    'focus_on_editable_field': True,
                    'is_system_key': False,
                    'modifiers': modifiers
                })
            else:
                continue

        buffer = ''


class LoadHandler(object):
    def OnLoadingStateChange(self, browser, is_loading, **_):
        """Called when the loading state has changed."""
        if not is_loading:
            # Loading is complete
            sys.stdout.write(os.linesep)
            print("[screenshot.py] Web page loading is complete")

            # Start event handling...
            print("[screenshot.py] Running thread to handle events from Blender...")
            self.thread = threading.Thread(target=handle_events, args=(browser,), name='b3d_cef_handle_events')
            self.thread.start()

            ## print("[screenshot.py] Will save screenshot in 2 seconds")
            # Give up to 2 seconds for the OnPaint call. Most of the time
            # it is already called, but sometimes it may be called later.
            ## CEF.PostDelayedTask(cef.TID_UI, 2000, save_screenshot, browser)
            CEF.PostDelayedTask(cef.TID_UI, 1000 * 60 * 60, exit_app, browser)

            # def click_button(browser: _Browser):
            #     browser.ExecuteJavascript("""
            #         document.getElementById('subscribe-btn').click();
            #     """)
            # CEF.PostDelayedTask(cef.TID_UI, 8000, click_button, browser)

    def OnLoadError(self, browser: _Browser, frame, error_code, failed_url, **_):
        """Called when the resource load for a navigation fails
        or is canceled."""
        if not frame.IsMain():
            # We are interested only in loading main url.
            # Ignore any errors during loading of other frames.
            return
        print("[screenshot.py] ERROR: Failed to load url: {url}"
              .format(url=failed_url))
        print("[screenshot.py] Error code: {code}"
              .format(code=error_code))
        # See comments in exit_app() why PostTask must be used
        CEF.PostTask(cef.TID_UI, exit_app, browser)


class RenderHandler(object):
    def __init__(self):
        self.OnPaint_called = False
        self.frame_count = 0
        self.start_time = time()

        # Start worker thread
        # t = threading.Thread(target=self.screenshot_worker, args=(writer,))
        # t.start()

    def GetViewRect(self, rect_out: list, **_) -> bool:
        """Called to retrieve the view rectangle which is relative
        to screen coordinates. Return True if the rectangle was
        provided."""
        # rect_out --> [x, y, width, height]
        rect_out.extend([0, 0, VIEWPORT_WIDTH, VIEWPORT_HEIGHT])
        return True

    # def OnCursorChange(self, browser: _Browser, cursor: int) -> None:
    #     """ Called when the browser's cursor has changed.
    #         If |type| is CT_CUSTOM then |custom_cursor_info| will be populated with the custom cursor information. """
    #     pass

    def OnPaint(self, browser: _Browser, element_type, paint_buffer: _PaintBuffer, **_) -> None:
        """Called when an element should be painted."""
        global SHM
        if SHM is None:
            print("Can't paint! SHM is not available!")
            return

        # Process a frame...
        self.frame_count += 1

        if self.OnPaint_called:
            sys.stdout.write(".")
            sys.stdout.flush()
        else:
            sys.stdout.write("[screenshot.py] OnPaint")
            self.OnPaint_called = True

        if element_type == cef.PET_VIEW:
            # Buffer string is a huge string, so for performance
            # reasons it would be better not to copy this string.
            # I think that Python makes a copy of that string when
            # passing it to SetUserData.
            ##  buffer_string = paint_buffer.GetBytes(mode="rgba", origin="top-left")

            # Browser object provides GetUserData/SetUserData methods
            # for storing custom data associated with browser.
            ## browser.SetUserData("OnPaint.buffer_string", buffer_string)

            # Convert the paint_buffer to a numpy array and reshape it to an image
            # image: np.ndarray = np.frombuffer(paint_buffer.GetBytes(mode="rgba", origin="top-left"), dtype=np.uint8)
            # image = image.reshape((browser.GetHeight(), browser.GetWidth(), 4))
            # Convert the numpy array to a PIL Image and save it
            # pil_image = Image.fromarray(image)
            # pil_image.save(SCREENSHOT_PATH)

            global TEXTURE_BUFFER

            image = Image.frombytes("RGBA", (VIEWPORT_WIDTH, VIEWPORT_HEIGHT), paint_buffer.GetBytes(mode="rgba", origin="top-left"), "raw", "RGBA", 0, 1)
            # image.save(SCREENSHOT_PATH, "PNG")
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

            print("[screenshot.py] Saved image: {path}".format(path=SCREENSHOT_PATH))

            # See comments in exit_app() why PostTask must be used
            # def _move_mousewheel(browser: _Browser):
            #     browser.SendMouseWheelEvent(x=100, y=100, deltaX=0, deltaY=-5)
            # CEF.PostTask(cef.TID_UI, _move_mousewheel, browser)
            # browser.SendMouseWheelEvent(x=100, y=100, deltaX=0, deltaY=-1)

        else:
            raise Exception("Unsupported element_type in OnPaint")

        # Calculate FPS every second
        if time() - self.start_time > 1.0:  # one second has passed
            fps = self.frame_count / (time() - self.start_time)
            print(f'[screenshot.py] FPS: {fps}')

            # Reset the frame count and start time
            self.frame_count = 0
            self.start_time = time()


class KeyboardHandler:
    
    def OnPreKeyEvent(self, browser: _Browser, event: dict, event_handle: object, is_keyboard_shortcut_out: list) -> bool:
        """ Called before a keyboard event is sent to the renderer. |event| contains information about the keyboard event.
            |event_handle| is the operating system event message, if any. Return true if the event was handled or false otherwise.
            If the event will be handled in OnKeyEvent() as a keyboard shortcut, set |is_keyboard_shortcut_out[0]| to True and return False. """
        return False

    def OnKeyEvent(self, browser: _Browser, event: dict, event_handle: object) -> bool:
        """ Called after the renderer and javascript in the page has had a chance to handle the event.
            |event| contains information about the keyboard event. |os_event| is the operating system event message, if any.
            Return true if the keyboard event was handled or false otherwise. Description of the KeyEvent type is in the OnPreKeyEvent() callback. """
        return False


if __name__ == '__main__':
    main()
