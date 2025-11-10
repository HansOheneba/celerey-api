from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import os

db = SQLAlchemy()

def create_app():
    load_dotenv()
    app = Flask(__name__)
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@"
        f"{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DB')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 280,
        "pool_pre_ping": True,
        "pool_size": 3, 
        "max_overflow": 5,
        "pool_timeout": 30,
    }

    db.init_app(app)

    from app.routes.insights import insights_bp
    from app.routes.podcasts import podcasts_bp
    from app.routes.advisors import advisors_bp
    from app.routes.contact import contact_bp
    from app.routes.webinars import webinars_bp

    app.register_blueprint(insights_bp, url_prefix="/api/insights")
    app.register_blueprint(podcasts_bp, url_prefix="/api/podcasts")
    app.register_blueprint(advisors_bp, url_prefix="/api/advisors")
    app.register_blueprint(contact_bp, url_prefix="/api/contact")
    app.register_blueprint(webinars_bp, url_prefix="/api/webinars")

    with app.app_context():
        db.create_all()

    return app
