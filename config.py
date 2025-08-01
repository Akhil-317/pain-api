from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os


load_dotenv()

class Settings(BaseSettings):
    database_hostname:str
    database_username:str
    database_port: str
    database_name: str
    database_password: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 180

    class Config:
        env_file=".env"


settings = Settings()

