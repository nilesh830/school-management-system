import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # Compute absolute paths relative to this config file so they are
    # independent of the working directory when the app is started.
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _INSTANCE_DIR = os.path.join(_BASE_DIR, 'instance')
    SCHOOLS_DB_DIR = os.path.join(_INSTANCE_DIR, 'schools')

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(_INSTANCE_DIR, 'schools', 'school_demo.db').replace('\\', '/')
    )
    SQLALCHEMY_BINDS = {
        'master': os.environ.get(
            'MASTER_DATABASE_URL',
            'sqlite:///' + os.path.join(_INSTANCE_DIR, 'master.db').replace('\\', '/')
        )
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:4200').split(',')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@school.sms')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'true').lower() == 'true'

    PASSWORD_RESET_EXPIRES_HOURS = 1
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:4200')


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SUPPRESS_SEND = True  # Log instead of send in dev


class ProductionConfig(Config):
    DEBUG = False
    MAIL_SUPPRESS_SEND = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_BINDS = {'master': 'sqlite:///:memory:'}
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    MAIL_SUPPRESS_SEND = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
