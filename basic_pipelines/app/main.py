from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Monter le répertoire static
app.mount("/static", StaticFiles(directory="/home/raspi/hailo-rpi5-examples/basic_pipelines/app/static"), name="static")

# Configurer les templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/stream", response_class=HTMLResponse)
async def read_stream(request: Request):
    return templates.TemplateResponse("stream.html", {"request": request})
