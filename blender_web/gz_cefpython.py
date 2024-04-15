import socket
import subprocess
from multiprocessing import shared_memory
import time
import struct
import numpy as np
from os import path
import threading
from queue import Queue
import asyncio

import bpy
import gpu
from bpy.types import Context, Event
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


from .utils.operator import OpsReturn
from .ackit import ACK
from .shaders import IMAGE_SHADER


SOCKET_LOCK = threading.Lock()

FPS = 30


#############################################################################################
#############################################################################################
#############################################################################################

class SOCKET_SIGNAL:
    PING = 0
    PONG = 1
    BUFFER_UPDATE = 2
    KILL = 3

    MOUSE_MOVE = 8
    MOUSE_PRESS = 9
    MOUSE_RELEASE = 10

    SCROLL_UP = 16
    SCROLL_DOWN = 17

    UNICODE = 24


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
    SOCKET_SIGNAL.MOUSE_MOVE        : 'II',    # (X, Y)
    SOCKET_SIGNAL.MOUSE_PRESS       : 'III',  # (X, Y, MOUSE_BUTTON)
    SOCKET_SIGNAL.MOUSE_RELEASE     : 'III',  # (X, Y, MOUSE_BUTTON)
    SOCKET_SIGNAL.SCROLL_UP         : 'II',    # (X, Y)
    SOCKET_SIGNAL.SCROLL_DOWN       : 'II',    # (X, Y)
    SOCKET_SIGNAL.UNICODE           : 'II'     # (UNICODE CODE, KeyEventFlags)
}


#############################################################################################
#############################################################################################
#############################################################################################


################################################################
################################################################
################################################################


@ACK.Deco.GZ({'VIEW_3D'})
class CEF_Python_Controller:
    texture: gpu.types.GPUTexture
    batch: gpu.types.GPUBatch
    shm_texture_buffer: np.ndarray
    gpu_buffer: gpu.types.Buffer


    # Initializing.
    # ----------------------------------------------------------------
    def __init__(self, context: Context) -> None:
        ## print("__init__")

        # Util properties.
        self.area_type = context.area.type
        self.width = context.region.width
        self.height = context.region.height
        self.mouse_pos = Vector((0, 0))
        self.prev_mouse_pos = Vector((0, 0))
        self.last_mouse_pos = Vector((0, 0))
        self.renderer_mouse_pos = (0, 0)

        # To messure FPS.
        self.draw_frame_count = 0
        self.draw_start_time = time.time()

        # States.
        self.is_running = False
        self.is_hovered = False
        self.is_dragging = False
        self.is_dirty = False

        # Runtime data.
        self._event_timer = None
        self.texture = None
        self.batch = None
        self.shm_texture_buffer = None
        self.gpu_buffer = None
        self.shm = None
        self.server = None
        self.client = None


    # Server and renderer management.
    # ----------------------------------------------------------------

    def start_server(self) -> None:
        # server = await asyncio.start_server(handle_client, '127.0.0.1', 0)
        # server.sockets[0].getsockname()
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # https://stackoverflow.com/questions/5875177/how-to-close-a-socket-left-open-by-a-killed-program
        # server.setblocking(0)
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        self.server = server
        self.host, self.port = server.getsockname()
        print("[SERVER] Setup server", server.getsockname())

    def start_thread(self) -> None:
        # bpy.app.timers.register(self.timer_client_receive)
        self.thread = threading.Thread(target=self.echo_server, daemon=True)
        self.thread.start()

    def start_renderer(self) -> None:
        python_executable = "X:/@jfranmatheu/BlenderWebStreaming/.env_cefpython/Scripts/python.exe"
        self.process = subprocess.Popen(
            [
                python_executable,
                path.join(path.dirname(__file__), 'scripts', 'bws_cefpython.py'),
                '--',
                'file://X:/@jfranmatheu/BlenderWebStreaming/blender_web/scripts/color_picker.html',
                f'{self.width},{self.height},{4}',
                self.shm.name,
                str(self.port)
            ],
            shell=True
        )

    def start_event_timer(self, context: Context):
        self._event_timer = context.window_manager.event_timer_add(1 / FPS, window=context.window)

    def start(self, context: Context) -> None:
        self.is_running = True
        self.first_connection = True

        # self.event_queue = Queue()

        ## print("START!")
        # self.start_thread()
        self.start_server()
        self.update_shm_buffer()
        self.update_batch()
        self.update_texture()
        self.start_renderer()
        self.start_event_timer(context)

        context.region.tag_redraw()

    def stop(self, context: Context) -> None:
        ## print("STOP!")
        context.region.tag_redraw()

        # Stop drawing.
        self.texture = None
        self.batch = None
        self.shm_texture_buffer = None
        self.gpu_buffer = None

        # Clear event Timer.
        if self._event_timer:
            context.window_manager.event_timer_remove(self._event_timer)
            self._event_timer = None

        # Close the socket reader flow.
        # if self.thread:
        #     self.thread = None
        # if bpy.app.timers.is_registered(self.timer_client_receive):
        #     bpy.app.timers.unregister(self.timer_client_receive)

        # Close client connection and close server.
        if client := self.client:
            try:
                client.send(SOCKET_SIGNAL.KILL.to_bytes(4, byteorder='big'))
            except socket.error as e:
                print(e)
            self.client = None
        if server := self.server:
            server.close()
            self.server = None

        # Terminate CEF process.
        if self.process:
            # self.process.terminate()
            self.process.kill()

        # Close SHM.
        if shm := self.shm:
            shm.close()
            shm.unlink()
            del shm

        self.is_running = False


    # SHM Management.
    # ----------------------------------------------------------------

    def update_batch(self) -> None:
        self.batch = batch_for_shader(IMAGE_SHADER, 'TRI_FAN', {"pos": [(0, 0), (self.width, 0), (self.width, self.height), (0, self.height)], "texco": [(0, 1), (1, 1), (1, 0), (0, 0)]})

    def update_shm_buffer(self) -> None:
        a = np.zeros((self.width * self.height * 4, ), dtype=np.float32)
        self.shm = shared_memory.SharedMemory(create=True, size=a.nbytes)
        b = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm.buf)
        b[:] = a[:]
        self.shm_texture_buffer = b
        self.shm_texture_buffer[-1] = 0
        self.gpu_buffer = gpu.types.Buffer('FLOAT', self.width * self.height * 4, self.shm_texture_buffer)
        del a

    def update_texture(self) -> None:
        if self.shm_texture_buffer is None:
            return
        try:
            self.texture = gpu.types.GPUTexture((self.width, self.height), format='RGBA32F', data=self.gpu_buffer)
        except Exception as e:
            print(e)


    # Sockets communication.
    # ----------------------------------------------------------------

    def ensure_client_connection(self) -> bool:
        if self.client is None:
            try:
                print("[SERVER] Trying to connect to client...")
                self.server.settimeout(10)
                self.client, addr = self.server.accept()
                self.server.settimeout(None)
                print("[SERVER] Client connected!", addr)
            except BlockingIOError:
                self.client = None
                return False
            except socket.error as e:
                print(e)
                self.client = None
                return False
        return True


    def echo_server(self) -> None:
        # https://realpython.com/python-sockets/
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            self.host, self.port = s.getsockname()
            self.server = s
            s.listen(1)
            while self.server is not None:
                conn, addr = s.accept()
                with conn:
                    self.client = conn
                    print(f"[SERVER] Connected by {addr}")
                    while self.server is not None:
                        try:
                            signal_raw = conn.recv(4)
                            if not signal_raw:
                                time.sleep(1/FPS)
                                continue
                        except BlockingIOError:
                            # Resource temporarily unavailable (errno EWOULDBLOCK)
                            time.sleep(1/FPS)
                            continue
                        except socket.error:
                            self.client = None
                            break

                        # Assume that the client is sending one 4-byte integer (signal) at a time
                        signal = int.from_bytes(signal_raw, byteorder='big')

                        # Handle the signal
                        if signal == SOCKET_SIGNAL.PING:
                            print("[SERVER] Received PING signal")
                            # Send back a PONG signal
                            conn.send(SOCKET_SIGNAL.PONG.to_bytes(4, byteorder='big'))
                        elif signal == SOCKET_SIGNAL.BUFFER_UPDATE:
                            print("[SERVER] Received BUFFER_UPDATE signal")
                            self.is_dirty = True
                        else:
                            print(f"[SERVER] Unknown signal: {signal}")


    def timer_client_receive(self) -> None:
        if self.server is None:
            return None

        if self.client is None:
            try:
                print("[SERVER] Trying to connect to client...")
                self.server.settimeout(5)
                self.client, addr = self.server.accept()
                self.server.settimeout(None)
                print("[SERVER] Client connected!", addr)
            except Exception as e:
                self.client = None
                return 0.1

        try:
            # Receive signals from the client.
            signal_raw = self.client.recv(4)
            if not signal_raw:
                return 1 / FPS

            # Assume that the client is sending one 4-byte integer (signal) at a time
            signal = int.from_bytes(signal_raw, byteorder='big')

            # Handle the signal
            if signal == SOCKET_SIGNAL.PING:
                print("[SERVER] Received PING signal")
                # Send back a PONG signal
                self.client.send(SOCKET_SIGNAL.PONG.to_bytes(4, byteorder='big'))
            elif signal == SOCKET_SIGNAL.BUFFER_UPDATE:
                print("[SERVER] Received BUFFER_UPDATE signal")
                self.is_dirty = True
            else:
                print(f"[SERVER] Unknown signal: {signal}")

        except socket.error as e:
            self.client = None

        return 1 / FPS

    def send(self, signal: int, *event_data: tuple) -> bool:
        def _send():
            # Send command ID.
            self.client.send(signal.to_bytes(4, byteorder='big'))

            # Is an Event? Send its data!
            if signal >= 8 and event_data:
                self.client.send(struct.pack(EVENT_DATA_BYTES[signal], *event_data))

        # attempt to send and receive wave, otherwise reconnect
        try:
            if self.client is None:
                raise socket.error("[SERVER] No client")
            _send()
        except socket.error as e:
            # set connection status and recreate socket
            self.connected = False
            self.client = None
            client = socket.socket()
            print("[SERVER] connection lost... reconnecting")
            ntries = 0
            while not self.connected:
                # attempt to reconnect, otherwise sleep for 2 seconds
                try:
                    client.connect((self.host, self.port))
                    self.connected = True
                    self.client = client
                    print("[SERVER] re-connection successful")
                    # Retry send data.
                    _send()
                    if self.first_connection:
                        self.first_connection = False
                except socket.error:
                    if self.first_connection:
                        # Avoid slowdown in first connection while client is loading...
                        break
                    if ntries >= 3:
                        break
                    ntries += 1
                    # time.sleep(.1)

    # Polling.
    # ----------------------------------------------------------------

    def poll_common(self, context: Context) -> bool:
        return True

    def poll_select(self, context: Context) -> bool:
        return self.poll_draw(context) and self.shm_texture_buffer is not None

    def poll_draw(self, context: Context) -> bool:
        return self.poll_common(context) and self.texture is not None and self.batch is not None


    # Internal methods.
    # ----------------------------------------------------------------

    @classmethod
    def _poll(self, context: Context, instance: 'CEF_Python_Controller') -> bool:
        if context.window_manager.show_gz_cefpython:
            if instance is not None and not instance.is_running:
                instance.start(context)
            if instance is not None and instance.process and instance.process.poll() is not None:
                # The client was closed due to some issue... Restart.
                print("[B3D] Client closed due to some issue. Restarting...")
                instance.process = None
                instance.stop(context)
            return True
        else:
            if instance is not None and instance.is_running:
                instance.stop(context)
            return False

    def _test_select(self, context: Context, loc) -> bool:
        ## print("_test_select")
        if not self.poll_select(context):
            ## print(self.shm_texture_buffer, self.texture, self.batch)
            return False
        a = self.get_pixel_alpha(*loc)
        is_hovered = a is not None and a > 0.01
        ## print("_test_select: alpha:", a, is_hovered)
        self.renderer_mouse_pos = (loc[0], self.height - loc[1])
        if is_hovered:
            self.prev_mouse_pos = self.mouse_pos.copy()
            self.mouse_pos = Vector(loc)
            if not self.is_hovered:
                self.mouse_enter(context, self.renderer_mouse_pos)
            self.mouse_move(context, self.renderer_mouse_pos)
        elif self.is_hovered:
            self.mouse_exit(context, self.renderer_mouse_pos)
        self.is_hovered = is_hovered
        return is_hovered

    def _invoke_prepare(self, context: Context) -> None:
        pass

    def _invoke(self, context: Context, event: Event) -> set[str]:
        ## print('_invoke')
        if not self.ensure_client_connection():
            return OpsReturn.CANCEL
        if event.type == 'TIMER':
            # self._event_timer.time_delta
            if self.is_dirty or self.shm_texture_buffer[-1] == 1:
                self.update_texture()
                self.shm_texture_buffer[-1] = 0
                self.is_dirty = False
                context.region.tag_redraw()
            return OpsReturn.PASS
        if self.invoke(context, event, self.renderer_mouse_pos):
            self.modal_enter(context, event)
            return OpsReturn.RUN
        else:
            return OpsReturn.FINISH

    def _modal(self, context: Context, event: Event, tweak) -> set[str]:
        ## print('_modal')
        if self.modal(context, event, self.renderer_mouse_pos):
            return OpsReturn.RUN
        return OpsReturn.FINISH

    def _exit(self, context: Context, cancel: bool) -> None:
        self.modal_exit(context, cancel)

    def _draw_prepare(self, context: Context) -> None:
        pass

    def _refresh(self, context: Context) -> None:
        if context.region.width != self.width or context.region.height != self.height:
            # TODO: do resize!
            pass

    def _draw(self, context: Context) -> None:
        if not self.poll_draw(context):
            return

        self.draw(context)

        self.draw_frame_count += 1
        # Calculate FPS every second
        if time.time() - self.draw_start_time > 1.0:  # one second has passed
            fps = self.draw_frame_count / (time.time() - self.draw_start_time)
            ## print(f'Draw-Handler FPS: {int(fps)}')

            # Reset the frame count and start time
            self.draw_frame_count = 0
            self.draw_start_time = time.time()


    # Mouse-Hover Events.
    # ----------------------------------------------------------------

    def mouse_enter(self, context: Context, mouse) -> None:
        pass

    def mouse_move(self, context: Context, mouse) -> None:
        threshold = 2 if self.is_dragging else 5
        if (self.mouse_pos - self.last_mouse_pos).length_squared < threshold:
            return
        ## print("mouse_move")
        self.last_mouse_pos = self.mouse_pos.copy()
        self.send(SOCKET_SIGNAL.MOUSE_MOVE, *mouse)

    def mouse_exit(self, context: Context, mouse) -> None:
        pass


    # Event handling.
    # ----------------------------------------------------------------

    def mouse_up(self, mouse, mouse_type: MOUSE_BUTTON) -> None:
        ## print("mouse_up")
        self.send(SOCKET_SIGNAL.MOUSE_RELEASE, *mouse, mouse_type)

    def mouse_down(self, mouse, mouse_type: MOUSE_BUTTON) -> None:
        ## print("mouse_down")
        self.send(SOCKET_SIGNAL.MOUSE_PRESS, *mouse, mouse_type)

    def invoke(self, context: Context, event: Event, mouse) -> bool:
        ## print("invoke")
        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'}:
            if event.value in {'PRESS', 'RELEASE'}:
                mouse_button = event.type.removesuffix('MOUSE')
                mouse_type: int = getattr(MOUSE_BUTTON, mouse_button)
                if event.value == 'RELEASE':
                    self.mouse_up(mouse, mouse_type)
                else:
                    self.mouse_down(mouse, mouse_type)
                return False

            elif event.type == 'LEFTMOUSE' and event.value == 'CLICK_DRAG':
                self.is_dragging = True
                return True
            else:
                return False

        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS':
            signal = SOCKET_SIGNAL.SCROLL_UP if event.type == 'WHEELUPMOUSE' else SOCKET_SIGNAL.SCROLL_DOWN
            self.send(signal, *mouse)
            return False

        elif event.unicode and event.value in {'PRESS', 'RELEASE'}:
            ##windows_vk_code = 0

            modififiers = KeyEventFlags.EVENTFLAG_NONE
            if event.alt:
                modififiers |= KeyEventFlags.EVENTFLAG_ALT_DOWN
            if event.shift:
                modififiers |= KeyEventFlags.EVENTFLAG_SHIFT_DOWN
            if event.ctrl:
                modififiers |= KeyEventFlags.EVENTFLAG_CONTROL_DOWN

            ## key_press = 1 if event.value == 'PRESS' else 0
            self.send(SOCKET_SIGNAL.UNICODE, ord(event.unicode), modififiers)
            return False

        return False

    def modal_enter(self, context: Context, event: Event) -> None:
        pass

    def modal(self, context: Context, event: Event, mouse) -> bool:
        if self.is_dragging:
            if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
                self.mouse_up('LEFT')
                return False
            if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                self.mouse_move(context, mouse)
            return True
        return False

    def modal_exit(self, context: Context, cancel: bool) -> None:
        self.is_dragging = False


    # Drawing.
    # ----------------------------------------------------------------
    def draw(self, context: Context) -> None:
        IMAGE_SHADER.uniform_sampler("image", self.texture)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(IMAGE_SHADER)
        gpu.state.blend_set('NONE')


    # Util methods.
    # ----------------------------------------------------------------

    def get_pixel_alpha(self, x: int, y: int) -> tuple | None:
        if self.shm_texture_buffer is None:
            return None
        pixel_index = (x * self.width + y) * 4
        if pixel_index >= len(self.shm_texture_buffer):
            return None
        return self.shm_texture_buffer[pixel_index + 3]


################################################################
################################################################


@ACK.Deco.UI_APPEND(bpy.types.VIEW3D_HT_header, poll=lambda header, ctx: True)
def ext_view3d_header(header, context: Context) -> None:
    header.layout.prop(context.window_manager, 'show_gz_cefpython', text='Interact!', toggle=True)


def init():
    ACK.Helper.PROP(bpy.types.WindowManager, 'show_gz_cefpython', ACK.Prop.BOOL(name="Interact!", default=False))


################################################################
################################################################


'''def unregister():
    for server in _socket_server_instances.values():
        if server:
            server.close()
    _socket_server_instances.clear()

    for shm in _shm_instances.values():
        if shm:
            shm.close()
            shm.unlink()
    _shm_instances.clear()
'''
