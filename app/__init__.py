from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from config.config import config
from app.models.show_metadata import db
import os

migrate = Migrate()

def create_app(config_name='default'):
    """Create and configure the Flask app"""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # Create storage directories
    os.makedirs(app.config['METADATA_STORAGE_PATH'], exist_ok=True)
    os.makedirs(app.config['FILES_STORAGE_PATH'], exist_ok=True)
    
    # Register blueprints
    from app.api.backup_routes import backup_bp
    from app.api.search_routes import search_bp
    
    app.register_blueprint(backup_bp, url_prefix='/api/backup')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    
    # Register main routes
    from app.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    return app 