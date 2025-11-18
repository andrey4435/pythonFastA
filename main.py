from fastapi import FastAPI, Request, Form, UploadFile, File, Cookie, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List
from models import Movietop
import os
import shutil
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import Body
import jwt

SECRET_KEY = "my_jwt_secret_key"
ALGORITHM = "HS256"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_current_user(authorization: str = Header(...)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username != "admin":
            raise HTTPException(status_code=401, detail="Invalid token user")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


movietop_list: List[Movietop] = [
    Movietop(id=1, name="Брат", cost=50, director="Алексей Балабанов", is_available=True),
    Movietop(id=2, name="Левиафан", cost=220, director="Андрей Звягинцев", is_available=True),
    Movietop(id=3, name="Движение вверх", cost=450, director="Антон Мегердичев", is_available=False),
    Movietop(id=4, name="Сталинград", cost=300, director="Фёдор Бондарчук", is_available=True),
    Movietop(id=5, name="Ирония судьбы, или С лёгким паром!", cost=70, director="Эльдар Рязанов", is_available=True),
    Movietop(id=6, name="Легенда №17", cost=250, director="Николай Лебедев", is_available=False),
    Movietop(id=7, name="9 рота", cost=170, director="Фёдор Бондарчук", is_available=True),
    Movietop(id=8, name="Т-34", cost=600, director="Алексей Сидоров", is_available=True),
    Movietop(id=9, name="Ёлки", cost=200, director="Тимур Бекмамбетов", is_available=False),
    Movietop(id=10, name="Адмиралъ", cost=280, director="Андрей Кравчук", is_available=True),
]


sessions = {}


@app.get("/")
def root():
    return {"message": "Сервер FastAPI запущен успешно!"}


@app.get("/study", response_class=HTMLResponse)
def get_study_info(request: Request):
    study_info = {
        "university": "Брянский государственный инженерно-технологический университет",
        "faculty": "Информационные технологии",
        "program": "Программная инженерия",
        "city": "Брянск",
        "photo_url": "/static/orig.jpeg"
    }
    return templates.TemplateResponse("study.html", {"request": request, "study_info": study_info})


@app.get("/movietop", response_model=List[Movietop])
def get_movietop():
    return movietop_list


@app.get("/add_movie", response_class=HTMLResponse)
def show_add_movie_form(request: Request):
    return templates.TemplateResponse("add_movie.html", {"request": request})


@app.post("/add_movie")
@app.post("/add_movie")
async def add_movie(
    name: str = Form(...),
    director: str = Form(...),
    cost: int = Form(...),
    is_available: bool = Form(False),
    description_file: UploadFile = File(None),
    cover_file: UploadFile = File(None),
    current_user: str = Depends(get_current_user)
):

    new_id = max(m.id for m in movietop_list) + 1
    description_path = None
    cover_path = None

    if description_file:
        desc_dir = "uploads/descriptions"
        os.makedirs(desc_dir, exist_ok=True)
        desc_filename = f"{new_id}_{description_file.filename}"
        desc_path = os.path.join(desc_dir, desc_filename)
        with open(desc_path, "wb") as buffer:
            shutil.copyfileobj(description_file.file, buffer)
        description_path = f"/uploads/descriptions/{desc_filename}"

    if cover_file:
        cover_dir = "uploads/covers"
        os.makedirs(cover_dir, exist_ok=True)
        cover_filename = f"{new_id}_{cover_file.filename}"
        cover_path_full = os.path.join(cover_dir, cover_filename)
        with open(cover_path_full, "wb") as buffer:
            shutil.copyfileobj(cover_file.file, buffer)
        cover_path = f"/uploads/covers/{cover_filename}"

    new_movie = Movietop(
        id=new_id,
        name=name,
        director=director,
        cost=cost,
        is_available=is_available,
        cover_url=cover_path,
        description_url=description_path
    )
    movietop_list.append(new_movie)

    return RedirectResponse(url="/movies", status_code=303)

@app.get("/movies", response_class=HTMLResponse)
def show_movies(request: Request):
    return templates.TemplateResponse("movies.html", {"request": request, "movies": movietop_list})


@app.get("/login", response_class=HTMLResponse)
def show_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "12345":
        token = str(uuid4())
        now = datetime.now()

        sessions[token] = {
            "username": username,
            "login_time": now,
            "expires_at": now + timedelta(minutes=2)
        }

        response = RedirectResponse(url="/movies", status_code=303)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="strict",
            max_age=120
        )
        return response

    return JSONResponse({"message": "Неверный логин или пароль"}, status_code=401)


@app.get("/user")
def get_user_profile(session_token: str = Cookie(None)):
    if not session_token or session_token not in sessions:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)

    now = datetime.now()
    data = sessions[session_token]

    if now > data["expires_at"]:
        del sessions[session_token]
        return JSONResponse({"message": "Session expired"}, status_code=401)

    data["expires_at"] = now + timedelta(minutes=2)

    all_sessions = [{
        "username": s["username"],
        "login_time": s["login_time"].strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": s["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
    } for s in sessions.values()]

    return {
        "current_session": {
            "username": data["username"],
            "login_time": data["login_time"].strftime("%Y-%m-%d %H:%M:%S"),
            "expires_at": data["expires_at"].strftime("%Y-%m-%d %H:%M:%S"),
        },
        "all_sessions": all_sessions,
        "movies": [m.dict() for m in movietop_list]
    }

@app.post("/login_json")
def login_json(payload: dict = Body(...)):
    username = payload.get("username")
    password = payload.get("password")

    if username != "admin" or password != "12345":
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid username or password"}
        )

    expire = datetime.utcnow() + timedelta(minutes=10)

    token_payload = {
        "sub": username,
        "role": "admin",
        "exp": expire
    }

    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": 10
    }




app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")



