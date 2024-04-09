# Blender Web Streaming

## Pyppeteer implementation

Implementation is based on Python 3.10, but could easily support a greater version.

### Setup Virtual Environment

1. Create Virtual Environment: `virtualenv .env_pyppeteer --python=python3.10`
2. (Windows-Only, if point 3 gives permissions error) `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
3. Activate new virtual environment in current terminal: `.\.env_pyppeteer\Scripts\activate`
4. Install requirements: `pip install -r requirements_pyppeteer.txt`


## CEF-Python implementation

Requires Python 3.9, latest CEFPython version won't work with higher versions. Also latest supported Chromium version is 66.

### Setup Virtual Environment

1. Create Virtual Environment: `virtualenv .env_cefpython --python=python3.9`
2. (Windows-Only, if point 3 gives permissions error) `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`
3. Activate new virtual environment in current terminal: `.\.env_cefpython\Scripts\activate`
4. Install requirements: `pip install -r requirements_cefpython.txt`
