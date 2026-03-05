from extensions import db
from models import User
from datetime import datetime


class AuthManager:
    """Logique métier d'authentification."""

    @staticmethod
    def get_or_create_user(user_info: dict) -> User:
        user = User.query.filter_by(google_id=user_info['sub']).first()
        if user is None:
            user = User(
                google_id   = user_info['sub'],
                email       = user_info['email'],
                name        = user_info.get('name', ''),
                given_name  = user_info.get('given_name', ''),
                family_name = user_info.get('family_name', ''),
                picture     = user_info.get('picture', ''),
            )
            db.session.add(user)
        else:
            user.name    = user_info.get('name', user.name)
            user.picture = user_info.get('picture', user.picture)

        user.last_login = datetime.utcnow()
        db.session.commit()
        return user

    @staticmethod
    def update_preferences(user: User, prefs: dict) -> User:
        current = user.preferences
        current.update(prefs)
        user.preferences = current
        db.session.commit()
        return user
