from app import create_app
from app.models import db, Podcasts

app = create_app()
with app.app_context():
    print(db.engine.url)
    print(Podcasts.query.count())
