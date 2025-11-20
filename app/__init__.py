from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
import mysql.connector
from mysql.connector import pooling

# Database connection pool
db_pool = None


def create_app():
    global db_pool
    load_dotenv()
    app = Flask(__name__)
    CORS(app)

    # Database configuration
    db_config = {
        "host": os.getenv("MYSQL_HOST"),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DB"),
        "port": os.getenv("MYSQL_PORT", 3306),
        "pool_name": "mypool",
        "pool_size": 3,
        "pool_reset_session": True,
    }

    # Create connection pool
    try:
        db_pool = pooling.MySQLConnectionPool(**db_config)
        print("Database connection pool created successfully")
    except Exception as e:
        print(f"Error creating connection pool: {e}")

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    from app.routes.insights import insights_bp
    from app.routes.podcasts import podcasts_bp
    from app.routes.advisors import advisors_bp
    from app.routes.contact import contact_bp
    from app.routes.webinars import webinars_bp
    from app.routes.plans import plans_bp
    from app.routes.leads import leads_bp
    

    app.register_blueprint(insights_bp, url_prefix="/api/insights")
    app.register_blueprint(podcasts_bp, url_prefix="/api/podcasts")
    app.register_blueprint(advisors_bp, url_prefix="/api/advisors")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")
    app.register_blueprint(webinars_bp, url_prefix="/api/webinars")
    app.register_blueprint(plans_bp, url_prefix="/api/plans")
    app.register_blueprint(leads_bp, url_prefix="/api/leads")

    return app


def get_db_connection():
    """Get a database connection from the pool"""
    if db_pool is None:
        raise Exception("Database pool not initialized")
    return db_pool.get_connection()
