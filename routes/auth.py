from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, bcrypt
from models import User
from datetime import datetime, timezone

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Veuillez remplir tous les champs.', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            login_user(user, remember=True)
            flash(f'Bienvenue, {user.username} !', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))

        flash('Email ou mot de passe incorrect.', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm', '')

        if not all([username, email, password, confirm]):
            flash('Veuillez remplir tous les champs.', 'danger')
            return render_template('register.html')

        if len(password) < 8:
            flash('Le mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('register.html')

        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur est déjà pris.", 'danger')
            return render_template('register.html')

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        user   = User(
            username=username,
            email=email,
            password_hash=hashed,
            name=username
        )
        db.session.add(user)
        db.session.commit()
        flash('Compte créé ! Vous pouvez vous connecter.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Déconnecté avec succès.', 'info')
    return redirect(url_for('auth.login'))