import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///archive_backup.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Archive.org API settings
    ARCHIVE_BASE_URL = "https://archive.org/"
    REQUEST_TIMEOUT = 10000
    
    # Storage settings
    STORAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'storage')
    METADATA_STORAGE_PATH = os.path.join(STORAGE_PATH, 'metadata')
    FILES_STORAGE_PATH = os.path.join(STORAGE_PATH, 'files')
    
    # Celery settings for background tasks
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Collections config
    DEFAULT_COLLECTION = "GratefulDead"
    CREATOR_BASED_COLLECTIONS = ["etree", "PhilLeshAndFriends", "BobWeir"]

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://username:password@localhost:5432/archive_backup_prod'
    
    # Enhanced production settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }
    
    # Storage paths for production
    STORAGE_PATH = os.environ.get('STORAGE_PATH') or '/var/lib/archive_backup/storage'
    METADATA_STORAGE_PATH = os.environ.get('METADATA_STORAGE_PATH') or '/var/lib/archive_backup/storage/metadata'
    FILES_STORAGE_PATH = os.environ.get('FILES_STORAGE_PATH') or '/var/lib/archive_backup/storage/files'
    
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    
    # Performance settings
    REQUEST_TIMEOUT = int(os.environ.get('ARCHIVE_REQUEST_TIMEOUT', 30000))

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 