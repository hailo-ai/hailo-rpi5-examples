# /home/raspi/hailo-rpi5-examples/basic_pipelines/app/main.py

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import models, schemas, crud, utils, database, oauth2

from .config import ADMIN_PASSWORD  # Importer ADMIN_PASSWORD

app = FastAPI()

# Configurer les templates
templates = Jinja2Templates(directory="/home/raspi/hailo-rpi5-examples/basic_pipelines/app/templates")

# Permettre les CORS si nécessaire
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modifier en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer les tables si elles n'existent pas
models.Base.metadata.create_all(bind=database.engine)


# Monter le répertoire static
app.mount("/static", StaticFiles(directory="/home/raspi/hailo-rpi5-examples/basic_pipelines/app/static"), name="static")

# Gestionnaire d'exceptions pour rediriger les 401 vers /login
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return RedirectResponse(url="/error", status_code=exc.status_code)  # Optionnel: gérer d'autres erreurs


# Page d'accueil (login requis)
@app.get("/", response_class=HTMLResponse)
async def read_home(request: Request, current_user: schemas.User = Depends(oauth2.get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": current_user})

# Page de login
@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Page d'inscription
@app.get("/register-page", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Endpoint d'inscription avec vérification du mot de passe admin
@app.post("/register", response_model=schemas.User)
def register(user: schemas.UserRegister, db: Session = Depends(oauth2.get_db)):
    # Vérifier le mot de passe admin
    if user.admin_password != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid admin password")

    # Vérifier si le username ou l'email existe déjà
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Créer le nouvel utilisateur
    return crud.create_user(db=db, user=schemas.UserCreate(username=user.username, email=user.email, password=user.password))


# Endpoint de connexion (login)
@app.post("/token", response_model=schemas.Token)
def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(oauth2.get_db)):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user:
        user = crud.get_user_by_email(db, email=form_data.username)  # Permettre la connexion par email
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    # Définir le token dans un cookie sécurisé
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,      # Accessible uniquement par le serveur
        secure=True,        # Transmis uniquement via HTTPS
        samesite='strict'   # Protection CSRF
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint protégé pour obtenir les infos de l'utilisateur connecté
@app.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: schemas.User = Depends(oauth2.get_current_user)):
    return current_user

@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, current_user: schemas.User = Depends(oauth2.get_current_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})


# Page protégée (stream)
@app.get("/stream", response_class=HTMLResponse)
async def read_stream(request: Request, current_user: schemas.User = Depends(oauth2.get_current_user)):
    return templates.TemplateResponse("stream.html", {"request": request, "user": current_user})

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"msg": "Successfully logged out"}
