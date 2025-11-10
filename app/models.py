from datetime import datetime
from . import db


class Insights(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    author = db.Column(db.String(120), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    excerpt = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(500))
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(255)) 


class Podcasts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    host = db.Column(db.String(120))
    duration = db.Column(db.String(50))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.Column(db.String(500))
    description = db.Column(db.Text)
    spotify_link = db.Column(db.String(500))
    spotify_embed_url = db.Column(db.String(500))
    tags = db.Column(db.String(255))


class Advisors(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text, nullable=False)
    experience = db.Column(db.Text, nullable=False)
    expertise = db.Column(db.Text)  # comma-separated list
    image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="new")  # new, read, replied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Webinar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(255))
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, nullable=False)
    speakers = db.Column(
        db.JSON
    ) 
    expectations = db.Column(db.JSON) 
    attendees = db.Column(db.JSON) 
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class WebinarRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    full_name = db.Column(db.String(255))
    status = db.Column(
        db.String(20), default="pending"
    )  # pending, invited, attended, cancelled
    invited_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
