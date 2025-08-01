from fastapi import FastAPI

from models.on_boarding_models import Base

from database import engine, DATABASE_URL

#for the sales_rep
from routes import client_on_boarding, file_validation, auth_routes
from fastapi.middleware.cors import CORSMiddleware

# from utils.seed_states import seed_states
# from utils.seed_countries import seed_countries_if_needed

print("Connecting to DB:", DATABASE_URL)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(file_validation.router)
app.include_router(client_on_boarding.router)

# @app.on_event("startup")
# def startup_tasks():
#     seed_countries_if_needed()
#     seed_states()


