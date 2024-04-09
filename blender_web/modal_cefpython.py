import socket
import threading
import subprocess
from multiprocessing import shared_memory
import sys
import queue
import time
import struct
import numpy as np
from os import path

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from .shaders import IMAGE_SHADER


FPS = 30

_sock = None
_client = None


class BWS_OT_web_navigator_cefpython(bpy.types.Operator):
    bl_idname = "bws.web_navigator_cefpython"
    bl_label = "CEF-Python"
    bl_description = "Web in Blender with CEF-Python"

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

        image: bpy.types.Image = bpy.data.images.get('Screenshot_CEFPython', None)
        if image is None:
            image = bpy.data.images.new("Screenshot_CEFPython", width=self.width, height=self.height, alpha=USE_ALPHA)
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

        server_port = self.start_server()

        # Start the Pyppeteer process in a new process to avoid blocking the UI
        # We need to use a virtual environment with Python 3.9...
        python_executable = "X:/@jfranmatheu/BlenderWebStreaming/.env_cefpython/Scripts/python.exe"
        # python_executable = path.join(path.dirname(path.abspath(__file__)), '.env_cefpython', 'Scripts', 'python.exe')
        self.process = subprocess.Popen(
            [
                python_executable,
                path.join(path.dirname(__file__), 'scripts', 'bws_cefpython.py'),
                '--',
                # "file://C:/Users/JF/Videos/AddonsMedia/2020-08-25_09-04-34.mp4",
                'file://X:/@jfranmatheu/BlenderWebStreaming/blender_web/scripts/test_web.html', # 'https://twitter.com/Blender', # 'https://youtu.be/_cMxraX_5RE',
                f'{context.region.width},{context.region.height},{channels}',
                self.shm.name,
                str(server_port)
            ],
            shell=True
        )

        # Start handlers.
        global FPS
        self._timer = context.window_manager.event_timer_add(1 / FPS, window=context.window)
        self._draw_handler = context.space_data.draw_handler_add(self.draw_handler, (), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def start_server(self) -> int:
        port = 8679
        global _sock
        global _client
        _client = None
        host = socket.gethostname()
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _sock.setblocking(0)  # set to non-blocking mode
        _sock.bind(('127.0.0.1', port))
        _sock.listen(1)
        ip, port = _sock.getsockname()
        print("Starting socket server..", ip, port)
        return port


    def modal(self, context, event):
        global _sock
        global _client

        if event.type == 'ESC':
            context.area.tag_redraw()

            # Clear event Timer.
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

            # Clear draw handler.
            context.space_data.draw_handler_remove(self._draw_handler, 'WINDOW')
            self._draw_handler = None

            # Close server.
            if _sock is not None:
                _sock.close()
                _sock = None
                _client = None

            # Terminate CEF process.
            if self.process:
                self.process.terminate()

            # Close SharedMemory block.
            if self.shm:
                self.shm.close()
                self.shm.unlink()
                del self.shm_texture_buffer
            return {'FINISHED'}

        region = context.region

        if event.type == 'TIMER':
            # Refresh GPUTexture from SharedMemory buffer.
            # self.image.pixels.foreach_set(self.shm_texture_buffer)
            # self.texture = gpu.texture.from_image(self.image)

            # pixels = width * height * array.array('f', [0.1, 0.2, 0.1, 1.0])
            # pixels = gpu.types.Buffer('FLOAT', width * height * 4, pixels)
            # self.texture = gpu.types.GPUTexture((width, height), format='RGBA16F', data=pixels)

            try:
                # No hace falta actualizar buffer al usar el mismo del SHM.
                # self.gpu_buffer[:] = self.shm_texture_buffer[:]
                # self.gpu_buffer = gpu.types.Buffer('FLOAT', self.width * self.height * 4, self.shm_texture_buffer)
                # Volcar buffuer actualizado a la GPU.
                self.texture = gpu.types.GPUTexture((self.width, self.height), format='RGBA32F', data=self.gpu_buffer)
            except Exception as e:
                print(e)

            # Refresh graphics.
            region.tag_redraw()

        # return {'RUNNING_MODAL'}

        if _client is None:
            try:
                _client, addr = _sock.accept()
                print('Connected by', addr)
            except BlockingIOError:
                return {'RUNNING_MODAL'}

        web_mouse_pos = (event.mouse_region_x, region.height - event.mouse_region_y)

        if event.type == 'TIMER':
            # If mouse was moved...
            if self.was_mouse_moved:
                self.was_mouse_moved = False
                _client.send(f"mousemove,{web_mouse_pos[0]},{web_mouse_pos[1]}\n".encode())
                self.mouse_pos = web_mouse_pos
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            self.was_mouse_moved = True
            return {'RUNNING_MODAL'}

        if event.type in {'LEFTMOUSE', 'RIGHTMOUSE', 'MIDDLEMOUSE'} and event.value in {'PRESS', 'RELEASE'}:
            # print("MOUSE_EVENT:", event.type, event.value)
            mouse_up = 1 if event.value == 'RELEASE' else 0
            mouse_button = event.type.removesuffix('MOUSE')
            _client.send(f"click,{web_mouse_pos[0]},{web_mouse_pos[1]},{mouse_up},{mouse_button}\n".encode())

        elif event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS':
            direction = -1 if event.type == 'WHEELUPMOUSE' else 1
            _client.send(f"scroll,{web_mouse_pos[0]},{web_mouse_pos[1]},{direction}\n".encode())

        elif event.unicode and not event.alt and not event.ctrl and not event.shift:
            _client.send(f"unicode,{event.unicode}\n".encode())

        return {'RUNNING_MODAL'}


    def draw_handler(self):
        if self.texture is None or self.batch is None:
            return

        self.draw_frame_count += 1

        IMAGE_SHADER.uniform_sampler("image", self.texture)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(IMAGE_SHADER)
        gpu.state.blend_set('NONE')

        # Calculate FPS every second
        if time.time() - self.draw_start_time > 1.0:  # one second has passed
            fps = self.draw_frame_count / (time.time() - self.draw_start_time)
            print(f'Draw-Handler FPS: {int(fps)}')

            # Reset the frame count and start time
            self.draw_frame_count = 0
            self.draw_start_time = time.time()


def draw_op(header, context):
    header.layout.operator('bws.web_navigator_cefpython')


def register():
    bpy.types.VIEW3D_HT_header.append(draw_op)

def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_op)
