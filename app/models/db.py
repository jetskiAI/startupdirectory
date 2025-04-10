from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    db.init_app(app)

    # Import models here to ensure they are registered with SQLAlchemy
    from app.models.startup import Startup, Founder

    return db
