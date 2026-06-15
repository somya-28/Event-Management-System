import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()

class Config:
    """Application configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Choose database type: 'mysql' or 'sqlite'
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
    
    if DB_TYPE == 'sqlite':
        # SQLite configuration (no installation needed)
        SQLALCHEMY_DATABASE_URI = 'sqlite:///event_management.db'
    else:
        # MySQL Database configuration
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_USER = os.getenv('DB_USER', 'root')
        DB_PASSWORD = os.getenv('DB_PASSWORD', '')
        DB_NAME = os.getenv('DB_NAME', 'event_management')
        
        # URL-encode password to handle special characters like @, #, etc.
        encoded_password = quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
        
        # SQLAlchemy configuration
        if DB_PASSWORD:
            SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}/{DB_NAME}'
        else:
            # No password specified
            SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}@{DB_HOST}/{DB_NAME}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
