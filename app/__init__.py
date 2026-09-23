from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import DATABASE_URL

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    from .routes import api
    app.register_blueprint(api)

    with app.app_context():
        from .models import Prediction
        db.create_all()

    return app
