from typing import Annotated
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from fastapi import Depends, FastAPI, HTTPException, Query
from config import settings

# PostgreSQL Database Configuration 
POSTGRES_USER = settings.database_username
POSTGRES_PASSWORD = settings.database_password
POSTGRES_DB = settings.database_name
POSTGRES_HOST = settings.database_hostname  # Change if using Docker or remote DB
POSTGRES_PORT = settings.database_port  # Default PostgreSQL port


DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print("Loaded DB config:")
print("HOST:", POSTGRES_HOST)
print("PORT:", POSTGRES_PORT)
print("USER:", POSTGRES_USER)
print("DB:", POSTGRES_DB)

# this is for session creation to communicate with the database with each request
def get_db():
    db= sessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create PostgreSQL Engine
# Engine is used to establish a connection with the database
engine = create_engine(DATABASE_URL)

sessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

Base = declarative_base()

