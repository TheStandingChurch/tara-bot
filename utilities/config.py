import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration for XAMPP
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),  # XAMPP MySQL runs on localhost
    "user": os.getenv("DB_USER", "root"),       # Default username for XAMPP MySQL
    "password": os.getenv("DB_PASSWORD", ""),   # No password
    "database": os.getenv("DB_NAME", "messages"),
    "port": 3306,
}
