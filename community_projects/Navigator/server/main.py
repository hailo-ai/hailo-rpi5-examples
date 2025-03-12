from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from starlette.requests import Request
import logging
import uvicorn
import json
import subprocess
import sys
sys.path.append("/home/pi/navigaitor/community_projects/Navigaitor/xfeat")
from server.move import move

# Initialize the FastAPI app
app = FastAPI()

# Set up logging (optional, for debugging)
logging.basicConfig(level=logging.INFO)
record_pid = 0 ;
@app.post("/call_function_start_record")
async def call_function_start_record():
    print("call_function_start_record: Button was pressed!")
 
    venv_python = '/home/pi/navigaitor/venv_hailo_rpi5_examples/bin/python'
    script_path = 'hailo_demo.py --record'
    record_pid = subprocess.Popen([venv_python, script_path], capture_output=True, text=True)

@app.post("/call_function_stop_record")
async def call_function_stop_record():
    record_pid.kill()

@app.post("/call_function_repeat_course")
async def call_function_repeat_course():
    print("call_function_repeat_course: Button was pressed!")


@app.post("/call_function_retreat_home")
async def call_function_retreat_home():
    print("call_function_retreat_home: Button was pressed!")
    venv_python = '/home/pi/navigaitor/venv_hailo_rpi5_examples/bin/python'
    script_path = 'hailo_demo.py --retreat'
    record_pid = subprocess.Popen([venv_python, script_path], capture_output=True, text=True)


# expecting: json in the format of `{"pressed" or "released": "forward" or "backward" or "left" or "right"}`
@app.websocket("/move")
async def move_robot(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        logging.info(f"Received message: {data}")
        move(json.loads(data))

# Endpoint to serve the HTML page with WebSocket client-side JavaScript
@app.get("/", response_class=FileResponse)
async def get_keypress_page(request: Request):
    # Render the HTML with embedded JavaScript for key events
    return FileResponse('./templates/keypress.html') 

def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)

