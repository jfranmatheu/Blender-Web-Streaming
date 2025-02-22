from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Dict, Any
import json
import asyncio
from pydantic import BaseModel

class Event(BaseModel):
    type: str
    x: int = 0
    y: int = 0
    key: int = 0
    modifiers: Dict[str, bool] = {}

class WebEvent(BaseModel):
    type: str
    element_id: str
    element_type: str
    value: Any = None
    extra: Dict[str, Any] = {}

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connected clients
blender_ws = None
qt_ws = None
web_ws = None

@app.websocket("/ws/blender")
async def blender_endpoint(websocket: WebSocket):
    await websocket.accept()
    global blender_ws
    blender_ws = websocket
    try:
        while True:
            # Receive events from Blender
            data = await websocket.receive_json()
            event = Event(**data)
            
            # Forward to Qt
            if qt_ws:
                await qt_ws.send_json(event.dict())
            
    except Exception as e:
        print(f"Blender websocket error: {e}")
    finally:
        blender_ws = None

@app.websocket("/ws/qt")
async def qt_endpoint(websocket: WebSocket):
    await websocket.accept()
    global qt_ws
    qt_ws = websocket
    try:
        while True:
            # Receive events from Qt
            data = await websocket.receive_json()
            
            # Forward to appropriate client
            if data.get("target") == "blender" and blender_ws:
                await blender_ws.send_json(data)
            elif data.get("target") == "web" and web_ws:
                await web_ws.send_json(data)
                
    except Exception as e:
        print(f"Qt websocket error: {e}")
    finally:
        qt_ws = None

@app.websocket("/ws/web")
async def web_endpoint(websocket: WebSocket):
    await websocket.accept()
    global web_ws
    web_ws = websocket
    try:
        while True:
            # Receive events from web
            data = await websocket.receive_json()
            web_event = WebEvent(**data)
            
            # Forward to Qt
            if qt_ws:
                await qt_ws.send_json(web_event.dict())
            
    except Exception as e:
        print(f"Web websocket error: {e}")
    finally:
        web_ws = None

@app.get("/element")
async def get_element_at(x: int, y: int):
    """Get element info at coordinates"""
    if qt_ws:
        await qt_ws.send_json({
            "type": "get_element",
            "x": x,
            "y": y
        })
        # Wait for response from Qt
        data = await qt_ws.receive_json()
        return data
    return {"error": "Qt not connected"}

def run_server():
    """Run the FastAPI server"""
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    run_server() 