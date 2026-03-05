import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-changez-en-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "database", "app.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    # Dossiers
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    PROCESSED_FOLDER = os.path.join(BASE_DIR, 'processed')
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports_out')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Mo
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'xml'}


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
