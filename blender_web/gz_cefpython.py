import socket
import threading
import subprocess
from multiprocessing import shared_memory
import sys
import queue
import time
import struct
import numpy as np

import bpy
import gpu
from bpy.types import Context, Event
from gpu_extras.batch import batch_for_shader
from mathutils import Vector


from .utils.operator import OpsReturn
from .ackit.reg_types.gz import RegisterGZ
from .ackit.reg_helpers.help_property import PropertyRegister


_socket_server_instances: list[socket.socket] = []
_shm_instances: list[shared_memory.SharedMemory] = []


@RegisterGZ({'VIEW_3D'})
class CEF_Python_Controller:

    texture: gpu.types.GPUTexture
    batch: gpu.types.GPUBatch

    server: socket.socket
    client: socket.socket

    # Initializing.
    # ----------------------------------------------------------------
    def __init__(self, context: Context) -> None:
        self.texture = None
        self.batch = None
        self.start_server()

    def start_server(self) -> int:
        host = socket.gethostname()
        _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _sock.setblocking(0)  # set to non-blocking mode
        _sock.bind(('127.0.0.1', 0))
        _sock.listen(1)
        self.server = _sock


    # Polling.
    # ----------------------------------------------------------------

    def poll(self, context: Context) --> bool:
        

    def poll_common(self, context: Context) -> bool:
        return True

    def poll_select(self, context: Context) -> bool:
        

    def poll_draw(self, context: Context) -> bool:
        return self.poll_common(context) and self.texture is not None and self.batch is not None


    # Internal methods.
    # ----------------------------------------------------------------

    def _test_select(self, context: Context, loc) -> bool:
        if self.poll_select(context): return False
        return self.

    def _invoke(self, context: Context) -> set[str]:
        

    def _draw(self, context: Context) -> None:
        if not self.poll_draw(context):
            return

        self.draw_frame_count += 1

        self.draw(context)

        # Calculate FPS every second
        if time.time() - self.draw_start_time > 1.0:  # one second has passed
            fps = self.draw_frame_count / (time.time() - self.draw_start_time)
            print(f'Draw-Handler FPS: {int(fps)}')

            # Reset the frame count and start time
            self.draw_frame_count = 0
            self.draw_start_time = time.time()


    # Event handling.
    # ----------------------------------------------------------------



    # Drawing.
    # ----------------------------------------------------------------
    def draw(self, context: Context) -> None:
        IMAGE_SHADER.uniform_sampler("image", self.texture)
        gpu.state.blend_set('ALPHA')
        self.batch.draw(IMAGE_SHADER)
        gpu.state.blend_set('NONE')


    # Util methods.
    # ----------------------------------------------------------------

    def get_pixel(self, x: int, y: int) -> tuple | None:
        if self.texture is not None:
            return None



def unregister():
    for server in _socket_server_instances:
        server.close()

    for shm in _shm_instances:
        shm.close()
        shm.unlink()
    _shm_instances.clear()
