import bpy
import gpu
import socket
import struct
import numpy as np
from gpu.types import GPUTexture, Buffer
from gpu_extras.batch import batch_for_shader
from multiprocessing import shared_memory
from bpy.types import Operator

class EventClient:
    def __init__(self, host='localhost', port=65432):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        
    def connect(self):
        """Establish connection to server"""
        try:
            if self.sock:
                self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print(f"[CLIENT] Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            self.connected = False
            return False
            
    def send_event(self, event_type, x, y, key):
        """Send event to server, reconnecting if necessary"""
        if not self.connected:
            if not self.connect():
                return False
                
        try:
            self.sock.sendall(struct.pack('!IiiI', event_type, x, y, key))
            return True
        except Exception as e:
            print(f"[CLIENT] Send failed: {e}")
            self.connected = False
            return False
            
    def close(self):
        """Close connection"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        self.connected = False

class ModalOperator(Operator):
    bl_idname = "wm.modal_operator"
    bl_label = "Modal Operator"

    def init(self):
        self._timer = None
        self._handle = None
        self.event_client = EventClient()
        self.event_client.connect()
        self.mouse_pos = (0, 0)

        # Initialize texture
        self.width = 1024
        self.height = 768
        self.channels = 4
        
        # Initialize shared memory
        self.shared_memory = shared_memory.SharedMemory(name="BWS_SharedMemoryBuffer")
        self.update_texture()
        
    def update_texture(self):
        if self.shared_memory.buf is not None:
            print("Updating texture")
            # Change to uint8 to match web renderer's RGBA8888 format
            self.shm_texture_buffer = np.ndarray((self.width * self.height * self.channels,), dtype=np.uint8, buffer=self.shared_memory.buf)
            # Convert uint8 [0-255] to float32 [0-1] for GPU
            float_buffer = self.shm_texture_buffer.astype(np.float32) / 255.0
            # Flip vertically
            float_buffer = float_buffer.reshape(self.height, self.width, self.channels)[::-1, :, :].flatten()
            self.gpu_buffer = Buffer('FLOAT', self.width * self.height * self.channels, float_buffer)
            self.texture = GPUTexture((self.width, self.height), format='RGBA32F', data=self.gpu_buffer)
        else:
            self.shm_texture_buffer = None
            self.gpu_buffer = None
            self.texture = None

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        
        if event.type.startswith('TIMER'):
            self.update_texture()
            context.region.tag_redraw()
            return {'PASS_THROUGH'}

        if event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self.update_mouse_coords(context, event)

        return self.handle_event(context, event)
    
    def update_mouse_coords(self, context: bpy.types.Context, event: bpy.types.Event):
        # Get viewport dimensions and scale mouse coordinates
        region = context.region
        scale_x = self.width / region.width
        scale_y = self.height / region.height
        
        # Scale mouse coordinates to match web view dimensions
        mouse_x = int(event.mouse_region_x * scale_x)
        mouse_y = int((region.height - event.mouse_region_y) * scale_y)
        
        # Keep coordinates in bounds
        mouse_x = max(0, min(mouse_x, self.width - 1))
        mouse_y = max(0, min(mouse_y, self.height - 1))
        
        self.mouse_pos = (mouse_x, mouse_y)

    def handle_event(self, context: bpy.types.Context, event: bpy.types.Event):
        """Handle Blender UI events"""
        try:
            # Pack modifier keys into the top 4 bits of the key value
            modifiers = 0
            if event.shift:
                modifiers |= (1 << 24)
            if event.ctrl:
                modifiers |= (1 << 25)
            if event.alt:
                modifiers |= (1 << 26)
            if event.oskey:
                modifiers |= (1 << 27)

            # Handle different event types
            if event.type == 'LEFTMOUSE':
                # Mouse click: type=0, key=0 for press, 1 for release
                key_value = (1 if event.value == 'RELEASE' else 0) | modifiers
                self.send_event(0, key_value)
                return {'RUNNING_MODAL'}
                
            elif event.type in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
                # Mouse move: type=2
                self.send_event(2, modifiers)
                return {'PASS_THROUGH'}

            elif event.type == 'WHEELUPMOUSE' or event.type == 'WHEELDOWNMOUSE':
                # Mouse wheel: type=1, key=delta value
                delta = 1 if event.type == 'WHEELUPMOUSE' else -1
                self.send_event(1, delta | modifiers)
                return {'RUNNING_MODAL'}

            elif event.ascii:
                # Unicode keyboard input: type=3, key=unicode value
                self.send_event(3, ord(event.ascii) | modifiers)
                return {'RUNNING_MODAL'}

            else:
                # Special keys: type=4, key=index into key_map
                special_keys = [
                    'DEL', 'RET', 'SPACE', 'BACK_SPACE',
                    'LEFT_ARROW', 'RIGHT_ARROW', 'UP_ARROW', 'DOWN_ARROW',
                    'TAB', 'ESC'
                ]
                
                if event.type in special_keys and event.value == 'PRESS':
                    key_index = special_keys.index(event.type)
                    self.send_event(4, key_index | modifiers)
                    return {'RUNNING_MODAL'}

            return {'PASS_THROUGH'}

        except Exception as e:
            print(f"[BLENDER] Error handling event: {e}")
            return {'PASS_THROUGH'}

    def send_event(self, event_type, key):
        """Send event to Qt process via socket"""
        self.event_client.send_event(event_type, *self.mouse_pos, key)

    def execute(self, context):
        self.init()
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / 30.0, window=context.window)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback, (self, context), 'WINDOW', 'POST_PIXEL')
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.area.tag_redraw()
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        self.event_client.close()
        self.shared_memory.close()

def draw_callback(self, context):
    if self.texture:
        shader = gpu.shader.from_builtin('IMAGE')
        shader.bind()
        shader.uniform_sampler('image', self.texture)
        gpu.state.blend_set('ALPHA')
        viewport_info = gpu.state.viewport_get()
        width, height = context.region.width, context.region.height
        gpu.state.viewport_set(0, 0, width, height)
        batch = batch_for_shader(shader, 'TRI_FAN', {
            "pos": ((0, 0), (width, 0), (width, height), (0, height)),
            "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
        })
        batch.draw(shader)
        gpu.state.blend_set('NONE')
        gpu.state.viewport_set(viewport_info[0], viewport_info[1], viewport_info[2], viewport_info[3])

def register():
    bpy.utils.register_class(ModalOperator)

def unregister():
    bpy.utils.unregister_class(ModalOperator)

if __name__ == "__main__":
    register()