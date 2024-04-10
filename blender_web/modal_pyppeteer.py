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


_sock = None
_client = None

q = queue.Queue()


buffer_size_1 = struct.calcsize('!II')
buffer_size_boolean = struct.calcsize('?')

is_texture_data_updated = False


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
        if True:
            data = _client.recv(buffer_size_boolean)
            if data:
                ### print("timer_callback:: texture is updated!")
                global is_texture_data_updated
                is_texture_data_updated = True
        else:
            data = _client.recv(buffer_size_1)
            if data:
                # Get the length of the image data
                width, height = struct.unpack('!II', data)
                length = width * height * 4
                print("Screenshot data... w, h, len:", width, height, length)
                _buffer = b""
                while len(_buffer) < length:
                    _buffer += _client.recv(length - len(_buffer))
                print("all buffer pixels ready")
                # texture_data = struct.unpack(f'!{length}I', buffer_data)
                arr = np.frombuffer(_buffer, dtype=np.uint8).astype(np.float16) / 255.0
                print("numpy arr ready")
                # Load the image data into a new image
                image: bpy.types.Image = bpy.data.images['Screenshot']
                if image.size[0] != width or image.size[1] != height:
                    image.scale(width, height)
                image.pixels.foreach_set(arr)
                print("pixels updated")
                global texture_buffer
                texture_buffer = gpu.texture.from_image(image)

    except BlockingIOError:
        pass
    return 0.01


class BWS_OT_web_navigator_pyppeteer(bpy.types.Operator):
    bl_idname = "bws.web_navigator_pyppeteer"
    bl_label = "Pyppeteer"
    bl_description = "Web in Blender with Pyppeteer"

    def invoke(self, context, event):
        self.shader = gpu.shader.from_builtin('IMAGE')
        self.batch = None
        self.width = 0
        self.height = 0
        self.texture = None
        
        self.draw_frame_count = 0
        self.draw_start_time = time.time()

        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))

        USE_ALPHA = True

        image: bpy.types.Image = bpy.data.images.get('Screenshot', None)
        if image is None:
            image = bpy.data.images.new("Screenshot", width=context.region.width, height=context.region.height, alpha=USE_ALPHA)
        else:
            image.scale(context.region.width, context.region.height)
        self.image = image

        # self.image = bpy.data.images.new('web_render.png', width=context.region.width, height=context.region.height, alpha=True)
        # self.image.filepath = path.join(path.dirname(__file__), 'web_render.png')
        # self.image.save(filepath=self.image.filepath)

        channels = self.image.channels

        a = np.empty((context.region.width * context.region.height * channels, ), dtype=np.float32)
        self.image.pixels.foreach_get(a)
        print(f"server:shm [shape:{a.shape}] [nbytes:{a.nbytes} nbytes/4:{a.nbytes / channels}]")
        self.shm = shared_memory.SharedMemory(create=True, size=a.nbytes)
        print("server:shm...np...buffer")
        b = np.ndarray(a.shape, dtype=a.dtype, buffer=self.shm.buf)
        b[:] = a[:]
        self.shm_texture_buffer = b

        # self.image.unpack(method='WRITE_LOCAL')  # 'WRITE_LOCAL', 'WRITE_ORIGINAL', 'USE_ORIGINAL', 'REMOVE', 'USE_LOCAL'
        # self.update_texture()

        self._draw_handler = context.space_data.draw_handler_add(self.draw_handler, (), 'WINDOW', 'POST_PIXEL')

        global _sock
        global _client
        _client = None
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _sock.setblocking(0)  # set to non-blocking mode
        _sock.bind(('127.0.0.1', 8671))
        _sock.listen(1)

        # Start the Pyppeteer process in a new process to avoid blocking the UI
        self.process = subprocess.Popen(
            [
                sys.executable,
                path.join(path.dirname(__file__), 'scripts', 'bws_pyppeteer.py'),
                '--',
                f'{context.region.width},{context.region.height},{channels}',
                self.shm.name,
                'file://X:/@jfranmatheu/BlenderWebStreaming/blender_web/scripts/test_web.html',
                self.image.filepath_raw
            ],
            shell=True
        )

        self._timer = context.window_manager.event_timer_add(0.2, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        print("invoke__end")
        return {'RUNNING_MODAL'}

    def update_texture(self, region) -> None:
        region.tag_redraw()
        return
        global is_texture_data_updated
        if is_texture_data_updated:
            ### print("draw_handler:: texture is updated!")
            self.image.pixels.foreach_set(self.shm_texture_buffer) # self.shm.buf)
            self.texture = gpu.texture.from_image(self.image)
            is_texture_data_updated = False
            region.tag_redraw()

        return
        if 'modified_at' not in self.image or self.image['modified_at'] != path.getmtime(self.image.filepath_raw):
            self.image['modified_at'] = path.getmtime(self.image.filepath_raw)
            self.image.reload()
            self.texture = gpu.texture.from_image(self.image)

    def modal(self, context, event):
        global _sock
        global _client

        # print("modal:", event.type, event.value)
        if event.type == 'ESC':
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
            # print("No websocket connection")
            return {'RUNNING_MODAL'}

        region = context.region
        web_mouse_pos = (event.mouse_region_x, region.height - event.mouse_region_y)

        if event.type == 'TIMER':
            v_web_mouse_pos = Vector(web_mouse_pos)
            self.update_texture(region)
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
        if self.width != region.width or self.height != region.height:
            self.width = region.width
            self.height = region.height
            self.batch = batch_for_shader(self.shader, 'TRI_FAN', {"pos": [(0, 0), (self.width, 0), (self.width, self.height), (0, self.height)], "texCoord": [(0, 1), (1, 1), (1, 0), (0, 0)]})
            _client.send(f"resize,{self.width},{self.height}\n".encode())

        return {'RUNNING_MODAL'}


    '''def run_client(self):
        print("Run Client! ... or trying...")
        async def client():
            uri = "ws://localhost:8766"
            async with websockets.connect(uri) as websocket:
                print("Hello client socket is connected! yay! finally shit!")
                while True: 
                    item = q.get()
                    if item is None:
                        time.sleep(0.1)
                        continue
                    if item == 'SHUTDOWN':
                        break
                    try:
                        websocket.send(item)
                        print("Client sent something:", item)
                    except Exception as e:
                        print("Client Socket failed... Say Bye o/")
                        break
                    q.task_done()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(client())
        loop.close()'''

    def draw_handler(self):
        ### global texture_buffer
        global is_texture_data_updated
        if is_texture_data_updated:
            ### print("draw_handler:: texture is updated!")
            self.image.pixels.foreach_set(self.shm_texture_buffer) # self.shm.buf)
            self.texture = gpu.texture.from_image(self.image)
            is_texture_data_updated = False
        if self.texture is None or self.batch is None:
            return
        
        self.draw_frame_count += 1

        self.shader.uniform_sampler("image", self.texture)
        self.batch.draw(self.shader)

        # Calculate FPS every second
        if time.time() - self.draw_start_time > 1.0:  # one second has passed
            fps = self.draw_frame_count / (time.time() - self.draw_start_time)
            print(f'Draw-Handler FPS: {fps}')

            # Reset the frame count and start time
            self.draw_frame_count = 0
            self.draw_start_time = time.time()


def draw_op(header, context):
    bpy.app.timers.register(timer_callback, first_interval=0.1)

    header.layout.operator('bws.web_navigator_pyppeteer')


def register():
    bpy.types.VIEW3D_HT_header.append(draw_op)

def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_op)
