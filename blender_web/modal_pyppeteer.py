import bpy
import websockets
import socket
import asyncio
import threading
import subprocess
from multiprocessing import Pool, shared_memory
import sys
import gpu
import queue
import time
import struct
import numpy as np
from os import path
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from .shaders import IMAGE_SHADER


_sock = None
_client = None

q = queue.Queue()


buffer_size_1 = struct.calcsize('!II')
buffer_size_boolean = struct.calcsize('?')

is_texture_data_updated = False

FPS = 30


def timer_callback():
    global _sock
    if _sock is None:
        return 1.0
    global _client
    if _client is None:
        try:
            _client, addr = _sock.accept()
            print('Connected by', addr)
        except BlockingIOError:
            _client = None
        return 0.01
    if not isinstance(_client, socket.SocketType):
        _client = None
        return 0.1
    try:
        data = _client.recv(buffer_size_boolean)
        if data:
            ### print("timer_callback:: texture is updated!")
            global is_texture_data_updated
            is_texture_data_updated = True
    except BlockingIOError:
        pass
    except OSError:
        _sock = None
        _client = None
        return None
    return 0.01


class BWS_OT_web_navigator_pyppeteer(bpy.types.Operator):
    bl_idname = "bws.web_navigator_pyppeteer"
    bl_label = "Pyppeteer"
    bl_description = "Web in Blender with Pyppeteer"

    def invoke(self, context, event):
        self.width = context.region.width
        self.height = context.region.height
        self.batch = batch_for_shader(IMAGE_SHADER, 'TRI_FAN', {"pos": [(0, 0), (self.width, 0), (self.width, self.height), (0, self.height)], "texco": [(0, 1), (1, 1), (1, 0), (0, 0)]})
        self.texture = None

        self.draw_frame_count = 0
        self.draw_start_time = time.time()

        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.was_mouse_moved = True

        USE_ALPHA = True

        image: bpy.types.Image = bpy.data.images.get('Screenshot_Pyppupeteer', None)
        if image is None:
            image = bpy.data.images.new("Screenshot_Pyppupeteer", width=self.width, height=self.height, alpha=USE_ALPHA)
        else:
            image.scale(self.width, self.height)
        self.image = image

        channels = self.image.channels

        a = np.zeros((self.width * self.height * channels, ), dtype=np.float32)
        # self.image.pixels.foreach_get(a)
        self.shm = shared_memory.SharedMemory(create=True, size=a.nbytes)
        b = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm.buf)
        b[:] = a[:]
        self.shm_texture_buffer = b
        self.gpu_buffer = gpu.types.Buffer('FLOAT', self.width * self.height * 4, self.shm_texture_buffer)
        self.texture = gpu.types.GPUTexture((self.width, self.height), format='RGBA32F', data=self.gpu_buffer)
        del a

        self._draw_handler = context.space_data.draw_handler_add(self.draw_handler, (), 'WINDOW', 'POST_PIXEL')

        server_socket = self.start_server()

        # Start the Pyppeteer process in a new process to avoid blocking the UI
        python_executable = "X:/@jfranmatheu/BlenderWebStreaming/.env_pyppeteer/Scripts/python.exe"
        self.process = subprocess.Popen(
            [
                # sys.executable,
                python_executable,
                path.join(path.dirname(__file__), 'scripts', 'bws_pyppeteer.py'),
                '--',
                str(server_socket),
                f'{context.region.width},{context.region.height},{channels}',
                self.shm.name,
                'file://X:/@jfranmatheu/BlenderWebStreaming/blender_web/scripts/test_web.html',
                self.image.filepath_raw,
            ],
            shell=True
        )

        self._timer = context.window_manager.event_timer_add(1 / FPS, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        print("invoke__end")
        return {'RUNNING_MODAL'}


    def start_server(self) -> int:
        global _sock
        global _client
        _client = None
        host = socket.gethostname()
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _sock.setblocking(0)  # set to non-blocking mode
        _sock.bind(('127.0.0.1', 0))
        _sock.listen(1)
        ip, port = _sock.getsockname()
        print("Starting socket server..", ip, port)
        return port


    def modal(self, context, event):
        global _sock
        global _client

        # print("modal:", event.type, event.value)
        if _sock is None or event.type == 'ESC':
            if _client:
                _client.close()
            if _sock:
                _sock.close()
            context.area.tag_redraw()
            context.window_manager.event_timer_remove(self._timer)
            context.space_data.draw_handler_remove(self._draw_handler, 'WINDOW')
            self._timer = None
            self._draw_handler = None
            if self.process:
                self.process.terminate()
            self.batch = None
            self.width = 0
            self.height = 0
            self.process = None
            self.image = None
            self.texture = None
            if self.shm:
                self.shm.close()
                self.shm.unlink()
            del self.shm_texture_buffer
            return {'FINISHED'}

        if _sock is None or _client is None:
            print("No websocket connection")
            return {'RUNNING_MODAL'}

        region = context.region
        web_mouse_pos = (event.mouse_region_x, region.height - event.mouse_region_y)

        region = context.region

        if event.type == 'TIMER':
            global is_texture_data_updated
            if is_texture_data_updated:
                is_texture_data_updated = False
                try:
                    self.texture = gpu.types.GPUTexture((self.width, self.height), format='RGBA32F', data=self.gpu_buffer)
                except Exception as e:
                    print(e)

            # Refresh graphics.
            region.tag_redraw()

            # Mousemove events.
            v_web_mouse_pos = Vector(web_mouse_pos)
            if (v_web_mouse_pos - self.mouse_pos).length_squared > 5:
                _client.send(f"mousemove,{web_mouse_pos[0]},{web_mouse_pos[1]}\n".encode())
                self.mouse_pos = v_web_mouse_pos

        elif event.type == 'MOUSEMOVE':
            pass
        elif event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'} and event.value == 'CLICK':
            mouse_button = event.type.removesuffix('MOUSE').lower()
            _client.send(f"click,{web_mouse_pos[0]},{web_mouse_pos[1]},{mouse_button}\n".encode())
        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS':
            direction = -1 if event.type == 'WHEELUPMOUSE' else 1
            _client.send(f"scroll,{direction * 24}\n".encode())
        else:
            return {'PASS_THROUGH'}

        # Update the batch and the browser window size if the region size has changed
        ## if self.width != region.width or self.height != region.height:
        ##     self.width = region.width
        ##     self.height = region.height
        ##     self.batch = batch_for_shader(IMAGE_SHADER, 'TRI_FAN', {"pos": [(0, 0), (self.width, 0), (self.width, self.height), (0, self.height)], "texCoord": [(0, 1), (1, 1), (1, 0), (0, 0)]})
        ##     _client.send(f"resize,{self.width},{self.height}\n".encode())

        return {'RUNNING_MODAL'}


    def draw_handler(self):
        if self.texture is None or self.batch is None:
            return

        self.draw_frame_count += 1

        IMAGE_SHADER.uniform_sampler("image", self.texture)
        self.batch.draw(IMAGE_SHADER)

        # Calculate FPS every second
        if time.time() - self.draw_start_time > 1.0:  # one second has passed
            fps = self.draw_frame_count / (time.time() - self.draw_start_time)
            print(f'Draw-Handler FPS: {fps}')

            # Reset the frame count and start time
            self.draw_frame_count = 0
            self.draw_start_time = time.time()

'''
def draw_op(header, context):
    bpy.app.timers.register(timer_callback, first_interval=0.1)

    header.layout.operator('bws.web_navigator_pyppeteer')


def register():
    bpy.types.VIEW3D_HT_header.append(draw_op)

def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_op)
'''