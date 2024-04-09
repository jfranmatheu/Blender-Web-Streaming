# Pyppeteer script

import os
import signal
import struct

import pyppeteer.page

PYPPETEER_CHROMIUM_REVISION = '1263111'
os.environ['PYPPETEER_CHROMIUM_REVISION'] = PYPPETEER_CHROMIUM_REVISION

import sys
import asyncio
import pyppeteer
import websockets
from time import time, sleep
from multiprocessing import shared_memory
import numpy as np
import base64
from PIL import Image
import io
import threading
import queue


START_WIDTH, START_HEIGHT, IMAGE_CHANNELS = [int(v) for v in sys.argv[-4].split(',')]
SHARED_MEMORY_ID = sys.argv[-3]
URL = sys.argv[-2]
RENDER_PATH = sys.argv[-1]
FPS = 24

print(sys.argv)

# Create a queue that can only hold 1 item at a time
texture_data_queue = queue.Queue(maxsize=1)


async def tcp_client():
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 8671)

    print("CLIENT:: connected to server!")

    args = pyppeteer.defaultArgs()
    if '--disable-gpu' in args:
        args.remove('--disable-gpu')
    args.append('--hide-scrollbars')
    args.append('--mute-audio')
    args.append('--enable-gpu-rasterization')
    args.append('--ignore-gpu-blocklist')
    # args.append('--use-gl=desktop')
    # args.append('--use-gl=egl')
    args.append('--use-gl=angle');args.append('--use-angle=gl-egl')
    browser = await pyppeteer.launch(
        {
            'headless': True,
            'ignoreDefaultArgs': True,
            'args': args
        },
    )

    page = await browser.newPage()
    await page.setViewport({"width": START_WIDTH, "height": START_HEIGHT})
    await page.goto(URL) # 'chrome://gpu'

    def _screenshot_worker(writer):
        print("client:shm")
        shm = shared_memory.SharedMemory(name=SHARED_MEMORY_ID)
        print("client:shm...np...buffer")
        texture_buffer = np.ndarray((START_WIDTH * START_HEIGHT * IMAGE_CHANNELS, ), dtype=np.float32, buffer=shm.buf)

        frame_count = 0
        start_time = time()

        while True:
            item = texture_data_queue.get()
            if item is None:
                continue
            if isinstance(item, str) and item == 'SHUTDOWN':
                break

            frame_count += 1

            # Decode the image data
            # screenshot_data = item
            image = Image.open(io.BytesIO(item)).convert("RGBA" if IMAGE_CHANNELS == 4 else "RGB")

            # Convert the image to a numpy array
            arr = np.array(image)
            # Convert the numpy array to float32
            arr = arr.astype(np.float32)
            # Normalize the values to be between 0 and 1
            arr /= 255.0
            # Flatten the array
            arr = arr.flatten()

            # Copy data to the texture buffer.
            texture_buffer[:] = arr[:]

            ### print("_screenshot_worker:: texture is updated!")

            # Notify the server that the texture data is updated!
            writer.write(struct.pack('?', True))

            # print("- Expected size:", texture_data.nbytes, "\t- Screenshot size:", arr.nbytes)
            texture_data_queue.task_done()

            image.close()
            del image
            del item
            del arr

            # Calculate FPS every second
            if time() - start_time > 1.0:  # one second has passed
                fps = frame_count / (time() - start_time)
                print(f'Render-Screen FPS: {fps}')

                # Reset the frame count and start time
                frame_count = 0
                start_time = time()

        del texture_buffer
        if shm:
            shm.close()

        print("CLIENT::_screenshot_worker -> CLOSE")

    # Start worker thread
    t = threading.Thread(target=_screenshot_worker, args=(writer,))
    t.start()

    print("CLIENT:: browser and page ready!")

    async def _handle_data(reader, page: pyppeteer.page.Page):
        buffer = ''

        while True:
            data = await reader.read(100)
            buffer += data.decode()
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                ### print("_handle_data:: Received data:", line)
                commands = line.split(',')
                command_id = commands[0]
                if command_id == 'mousemove':
                    x, y = map(int, commands[1:])
                    await page.mouse.move(x, y)
                    # force_screenshot = True
                elif command_id == 'click':
                    x, y = map(int, commands[1:-1])
                    mouse_button = commands[-1]
                    await page.mouse.click(x, y, options={'button': mouse_button})
                elif command_id == 'resize':
                    width, height = map(int, commands[1:])
                    await page.setViewport({"width": width, "height": height})
                    # force_screenshot = True
                elif command_id == 'scroll':
                    scroll_value: str = commands[-1]
                    await page.evaluate("{window.scrollBy(0," + scroll_value + ");}")
                    # force_screenshot = True

    async def _take_screenshots(writer, page):
        last_screenshot = time()
        refresh_time = 1.0 / FPS

        while True:
            if (time() - last_screenshot) > refresh_time:
                # await page.screenshot({'path': RENDER_PATH})
                # result = await page._client.send('Page.captureScreenshot', {'format': 'png'})
                # if encoding == 'base64':
                #     buffer = result.get('data', b'')
                # else:
                #     buffer = base64.b64decode(result.get('data', b''))
                if texture_data_queue.qsize() == 0:
                    screenshot = await page.screenshot({'encoding': 'binary'})
                    ### print("_take_screenshots:: screenshot")
                    texture_data_queue.put_nowait(screenshot)

                # Websockets implementation.
                ### screenshot = await page.screenshot({'encoding': 'base64'})
                ### print("Screenshot:", screenshot)
                ### width, height = page.viewport['width'], page.viewport['height']
                ### print(len(screenshot), width*height)
                ### # Send the width and height of the screenshot as 4-byte integers
                ### writer.write(struct.pack('!II', width, height))
                ### # Send the screenshot data
                ### writer.write(screenshot.encode()) # struct.pack(f'!{width*height*4}I', screenshot))
                last_screenshot = time()

    # Create tasks for handling data and taking screenshots
    task_1 = asyncio.create_task(_handle_data(reader, page))
    task_2 = asyncio.create_task(_take_screenshots(writer, page))

    try:
        # Run the tasks concurrently and wait for all of them to complete
        await asyncio.gather(task_1, task_2)
    except ConnectionResetError:
        print('Server closed the connection')
    except OSError as e:
        print(e)
    except Exception as e:
        print(e)
    finally:
        print('Closing the connection')
        task_1.cancel() # set_exception()
        task_2.cancel() # set_exception()
        writer.close()

    texture_data_queue.put('SHUTDOWN')
    t.join()


asyncio.run(tcp_client())
