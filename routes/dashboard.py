from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import CleaningHistory

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('login.html')
    recent = (CleaningHistory.query
              .filter_by(user_id=current_user.id)
              .order_by(CleaningHistory.created_at.desc())
              .limit(5).all())
    return render_template('dashboard.html', recent=recent)


@dashboard_bp.route('/history')
@login_required
def history():
    all_history = (CleaningHistory.query
                   .filter_by(user_id=current_user.id)
                   .order_by(CleaningHistory.created_at.desc())
                   .all())
    return render_template('history.html', history=all_history)
