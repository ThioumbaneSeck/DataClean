from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone
import json


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email         = db.Column(db.String(256), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name          = db.Column(db.String(256))
    given_name    = db.Column(db.String(128))
    family_name   = db.Column(db.String(128))
    picture       = db.Column(db.String(512))
    is_admin      = db.Column(db.Boolean, default=False)
    total_cleanings     = db.Column(db.Integer, default=0)
    total_rows_cleaned  = db.Column(db.Integer, default=0)
    _preferences  = db.Column('preferences', db.Text, default='{}')
    last_login    = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    created_at    = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    cleaning_history = db.relationship('CleaningHistory', backref='user', lazy='dynamic',
                                        cascade='all, delete-orphan')
    files = db.relationship('FileMeta', backref='user', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def preferences(self):
        return json.loads(self._preferences or '{}')

    @preferences.setter
    def preferences(self, value):
        self._preferences = json.dumps(value)

    def __repr__(self):
        return f'<User {self.email}>'


class CleaningHistory(db.Model):
    __tablename__ = 'cleaning_history'

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_name            = db.Column(db.String(256))
    original_rows        = db.Column(db.Integer)
    cleaned_rows         = db.Column(db.Integer)
    original_cols        = db.Column(db.Integer)
    duplicates_removed   = db.Column(db.Integer, default=0)
    missing_treated      = db.Column(db.Integer, default=0)
    outliers_treated     = db.Column(db.Integer, default=0)
    missing_method       = db.Column(db.String(64))
    outlier_method       = db.Column(db.String(64))
    normalization_method = db.Column(db.String(64))
    quality_score        = db.Column(db.Float)
    output_path          = db.Column(db.String(512))
    _stats               = db.Column('stats', db.Text, default='{}')
    created_at           = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    @property
    def stats(self):
        return json.loads(self._stats or '{}')

    @stats.setter
    def stats(self, value):
        self._stats = json.dumps(value)

    def __repr__(self):
        return f'<CleaningHistory {self.file_name}>'


class FileMeta(db.Model):
    __tablename__ = 'file_meta'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_name = db.Column(db.String(256))
    stored_name   = db.Column(db.String(256))
    file_path     = db.Column(db.String(512))
    file_hash     = db.Column(db.String(64))
    file_size     = db.Column(db.Integer)
    mime_type     = db.Column(db.String(128))
    status        = db.Column(db.String(64), default='uploaded')
    created_at    = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def __repr__(self):
        return f'<FileMeta {self.original_name}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))