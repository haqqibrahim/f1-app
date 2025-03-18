from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Query
from fastapi.templating import Jinja2Templates
from google.cloud import firestore
import os
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI()

# Set up Firestore
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "f1-app-d2ac7-firebase-adminsdk-fbsvc-596f9d853c.json"
db = firestore.Client()

# Firestore collections
drivers_ref = db.collection("drivers")
teams_ref = db.collection("teams")

# Driver Model
class Driver(BaseModel):
    name: str
    age: int
    total_pole_positions: int
    total_race_wins: int
    total_points_scored: int
    total_world_titles: int
    total_fastest_laps: int
    team: str

# Team Model
class Team(BaseModel):
    name: str
    year_founded: int
    total_pole_positions: int
    total_race_wins: int
    total_constructor_titles: int
    finishing_position_prev_season: int

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates directory
templates = Jinja2Templates(directory="templates")

def is_authenticated(request: Request):
    token = request.cookies.get("token")
    return token is not None and token != ""


# Serve the main page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Serve the Add Driver page
@app.get("/add_driver", response_class=HTMLResponse)
async def add_driver_page(request: Request):
    return templates.TemplateResponse("add_driver.html", {"request": request})

# Serve the Add Team page
@app.get("/add_team", response_class=HTMLResponse)
async def add_team_page(request: Request):
    return templates.TemplateResponse("add_team.html", {"request": request})

# Function to add driver
def add_driver(driver: Driver):
    driver_dict = driver.dict()
    drivers_ref.document(driver.name).set(driver_dict)

# Function to add team
def add_team(team: Team):
    team_dict = team.dict()
    teams_ref.document(team.name).set(team_dict)

@app.get("/add-driver", response_class=HTMLResponse)
async def add_driver_page(request: Request): # noqa: F811
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("add_driver.html", {"request": request})

@app.get("/add-team", response_class=HTMLResponse)
async def add_team_page(request: Request):  # noqa: F811
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("add_team.html", {"request": request})

@app.get("/query_drivers/", response_class=HTMLResponse)
async def query_drivers_page(request: Request):
    return templates.TemplateResponse("query_drivers.html", {"request": request})

@app.get("/search-drivers/")
async def search_drivers(attribute: str, comparison: str, value: float):
    """Search for drivers based on an attribute, comparison type, and value."""
    query = drivers_ref
    value = int(value) if attribute in ["age", "total_pole_positions", "total_race_wins", 
                                        "total_points_scored", "total_world_titles", "total_fastest_laps"] else value

    if comparison == "greater":
        query = query.where(attribute, ">", value)
    elif comparison == "less":
        query = query.where(attribute, "<", value)
    elif comparison == "equal":
        query = query.where(attribute, "==", value)
    else:
        return {"error": "Invalid comparison type"}

    results = query.stream()
    drivers = [doc.to_dict() for doc in results]

    return {"drivers": drivers}

@app.get("/query_teams/", response_class=HTMLResponse)
async def query_teams_page(request: Request):
    return templates.TemplateResponse("query_teams.html", {"request": request})

@app.get("/search-teams/")
async def search_teams(attribute: str, comparison: str, value: float):
    """Search for teams based on an attribute, comparison type, and value."""
    query = teams_ref
    value = int(value) if attribute in ["year_founded", "total_pole_positions", "total_race_wins",
                                        "total_constructor_titles", "finishing_position_prev_season"] else value

    if comparison == "greater":
        query = query.where(attribute, ">", value)
    elif comparison == "less":
        query = query.where(attribute, "<", value)
    elif comparison == "equal":
        query = query.where(attribute, "==", value)
    else:
        return {"error": "Invalid comparison type"}

    results = query.stream()
    teams = [doc.to_dict() for doc in results]

    return {"teams": teams}

@app.post("/add-driver")
async def add_driver_endpoint(driver: Driver):
    try:
        add_driver(driver)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-team")
async def add_team_endpoint(team: Team):
    try:
        add_team(team)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/driver/{driver_id}", response_class=HTMLResponse)
async def driver_details(request: Request, driver_id: str):
    """Fetch and display driver details."""
    driver_doc = drivers_ref.document(driver_id).get()

    if not driver_doc.exists:
        return HTMLResponse("<h3>Driver not found</h3>", status_code=404)

    driver = driver_doc.to_dict()
    return templates.TemplateResponse("driver_details.html", {"request": request, "driver": driver})


@app.get("/team/{team_id}", response_class=HTMLResponse)
async def team_details(request: Request, team_id: str):
    """Fetch and display team details."""
    team_doc = teams_ref.document(team_id).get()

    if not team_doc.exists:
        return HTMLResponse("<h3>Team not found</h3>", status_code=404)

    team = team_doc.to_dict()
    return templates.TemplateResponse("team_details.html", {"request": request, "team": team})

@app.post("/edit-driver/{driver_id}")
async def edit_driver(request: Request, driver_id: str, driver: Driver):
    if not is_authenticated(request):
        return {"error": "Unauthorized access"}
    drivers_ref.document(driver_id).update(driver.dict())
    return RedirectResponse(url=f"/driver/{driver_id}", status_code=302)

@app.post("/delete-driver/{driver_id}")
async def delete_driver(request: Request, driver_id: str):
    if not is_authenticated(request):
        return {"error": "Unauthorized access"}
    drivers_ref.document(driver_id).delete()
    return RedirectResponse(url="/query-drivers", status_code=302)

@app.post("/edit-team/{team_id}")
async def edit_team(request: Request, team_id: str, team: Team):
    if not is_authenticated(request):
        return {"error": "Unauthorized access"}
    teams_ref.document(team_id).update(team.dict())
    return RedirectResponse(url=f"/team/{team_id}", status_code=302)

@app.post("/delete-team/{team_id}")
async def delete_team(request: Request, team_id: str):
    if not is_authenticated(request):
        return {"error": "Unauthorized access"}
    teams_ref.document(team_id).delete()
    return RedirectResponse(url="/query-teams", status_code=302)

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/compare-drivers", response_class=HTMLResponse)
async def compare_drivers_page(request: Request):
    """Render the compare drivers page."""
    return templates.TemplateResponse("compare_drivers.html", {"request": request})

@app.get("/compare-teams", response_class=HTMLResponse)
async def compare_teams_page(request: Request):
    """Render the compare teams page."""
    return templates.TemplateResponse("compare_teams.html", {"request": request})


@app.get("/api/compare-teams")
async def compare_teams(team1: str = Query(...), team2: str = Query(...)):
    """Fetch two teams for comparison."""
    doc1 = teams_ref.document(team1).get()
    doc2 = teams_ref.document(team2).get()


    if not doc1.exists or not doc2.exists:
        return {"error": "One or both teams not found"}

    return {
        "team1": doc1.to_dict(),
        "team2": doc2.to_dict()
    }

# Add after the existing /api/compare-teams endpoint

@app.get("/api/compare-drivers")
async def compare_drivers(driver1: str = Query(...), driver2: str = Query(...)):
    """Fetch two drivers for comparison."""
    doc1 = drivers_ref.document(driver1).get()
    doc2 = drivers_ref.document(driver2).get()

    if not doc1.exists or not doc2.exists:
        return {"error": "One or both drivers not found"}

    return {
        "driver1": doc1.to_dict(),
        "driver2": doc2.to_dict()
    }