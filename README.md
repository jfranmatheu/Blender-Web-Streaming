# Blender Web Streaming

## Pyppeteer implementation

Implementation is based on Python 3.10, but could easily support a greater version.

### Limitations

- Does not have offscreen rendering as it is, you need to perform expensive screenshots.

### Setup Virtual Environment

1. Create Virtual Environment: `virtualenv .env_pyppeteer --python=python3.10`
2. (Windows-Only, if point 3 gives permissions error) `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
3. Activate new virtual environment in current terminal: `.\.env_pyppeteer\Scripts\activate`
4. Install requirements: `pip install -r requirements_pyppeteer.txt`

### Performance

While Pyppeteer offers great tools to navigate the web and you can use an up-to-date chromium version, it is not optimized for offscreen rendering, so you will likely get 5 FPS.

## CEF-Python implementation

Requires Python 3.9, latest CEFPython version won't work with higher versions. Also latest supported Chromium version is 66.

### Setup Virtual Environment

1. Create Virtual Environment: `virtualenv .env_cefpython --python=python3.9`
2. (Windows-Only, if point 3 gives permissions error) `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
3. Activate new virtual environment in current terminal: `.\.env_cefpython\Scripts\activate`
4. Install requirements: `pip install -r requirements_cefpython.txt`

### Performance

While there are several limitations when using an oldish chromium version, it has a nice support for offscreen rendering, delivering 60FPS with no effort on simple pages.

## PyQt5's QtWebEngine implementation

QtWebEngine works with Chromium, is up-to-date so we can use latest version of Python and Chromium!

### Limitations
- You need a virtual display or a virtual framebuffer as Xvfb.
- Event simulation is limited. While you can access DOM to get element at position to perform a click to it, etc. You can't have a mousemove event in the sense that the web is responsive to that motion.
- While it does offscreen rendering, we don't have a callback function to whenever the browser does a repaint (it does in the C++ Qt with a repaint signal), so we can update the shared memory buffer and notify Blender process about that refresh, also if using a timer or a thread you need to make sure that the refresh code is called from the main thread of the QApp.

### Setup Virtual Environment

1. Create Virtual Environment: `virtualenv .env_pyqt`
2. (Windows-Only, if point 3 gives permissions error) `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
3. Activate new virtual environment in current terminal: `.\.env_pyqt\Scripts\activate`
4. Install requirements: `pip install -r requirements_pyqt.txt`

### Performance

Good enough. Almost equivalent to CEF.
