from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Remplacez 'localhost' par l'adresse IP de votre RPi si nécessaire
    rpi_ip = "192.168.50.2"
    return templates.TemplateResponse("index.html", {"request": request, "rpi_ip": rpi_ip})

if __name__ == "__main__":
    # Lancer l'application sur le port 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
