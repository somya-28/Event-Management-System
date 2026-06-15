import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import pymysql

# Install PyMySQL as MySQLdb
pymysql.install_as_MySQLdb()

app = Flask(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure MySQL database using config.py
from config import Config
app.config.from_object(Config)

db = SQLAlchemy(app)

# Import models (make sure models.py exists and uses SQLAlchemy)
try:
    from models import User, Event, Guest, Booking
except ImportError as e:
    print(f"Error importing models: {e}")
    print("Make sure all your model classes are properly defined")
    exit(1)

def setup_database():
    """Setup MySQL database with tables and default admin user"""
    try:
        with app.app_context():
            print("Connecting to MySQL database...")
            
            # Test database connection
            db.engine.connect()
            print("✓ Connected to MySQL successfully!")
            
            # Drop all tables (be careful with this in production!)
            print("Dropping existing tables...")
            db.drop_all()
            
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("✓ Database tables created successfully!")
            
            # Create default admin user
            admin_user = User(
                username='admin',
                email='admin@gmail.com',
                full_name='Administrator',
                password_hash=generate_password_hash('admin123')
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("\n" + "="*50)
            print("🎉 MySQL Database setup complete!")
            print("="*50)
            print("Default admin user created:")
            print("Username: admin")
            print("Email: admin@gmail.com") 
            print("Password: admin123")
            print("="*50)
            print("\nYou can now run: python app.py")
            
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure MySQL server is running")
        print("2. Check your .env file has correct MySQL credentials")
        print("3. Verify the database 'event_management' exists")
        print("4. Ensure user has proper permissions")

if __name__ == '__main__':
    setup_database()
