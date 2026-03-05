# routes.py
from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def dashboard():
    return render_template('dashboard.html')

@main_bp.route('/history')
def history():
    return render_template('history.html')
# routes.py
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@main_bp.route('/history')
@login_required
def history():
    return render_template('history.html', user=current_user)

@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        f = request.files['file']
        # ici tu peux sauvegarder le fichier et lancer DataProcessor
        return redirect(url_for('main.dashboard'))
    return render_template('upload.html')