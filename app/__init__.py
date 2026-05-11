from flask import Flask
from flask_login import LoginManager
from config import Config
from app.models import db, User
import os

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions here
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.dashboard.routes import dashboard_bp
    from app.blueprints.subjects.routes import subjects_bp
    from app.blueprints.decks.routes import decks_bp
    from app.blueprints.flashcards.routes import flashcards_bp
    from app.blueprints.generate.routes import generate_bp
    from app.blueprints.study.routes import study_bp
    from app.blueprints.progress.routes import progress_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(subjects_bp)
    app.register_blueprint(decks_bp)
    app.register_blueprint(flashcards_bp)
    app.register_blueprint(generate_bp)
    app.register_blueprint(study_bp, url_prefix='/study')
    app.register_blueprint(progress_bp, url_prefix='/progress')

    return app
