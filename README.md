# DataClean API — M1 IAGE 2025/2026

API REST de traitement automatisé des données développée avec Flask.

## Auteurs

- Madame Coumba DIONE  
- Madame THIOUMBANE SECK  
- Madame Ndeye Anta DIAW  
- Monsieur Alpha THIMBO  

Encadrant : Monsieur Abdoulaye BARRO

---

## Fonctionnalités

- Authentification sécurisée via **Google OAuth 2.0**
- Import de fichiers **CSV, Excel, JSON, XML**
- **Suppression des doublons**
- **Traitement des valeurs manquantes** (moyenne, médiane, mode, suppression)
- **Détection des outliers** (IQR, Z-score)
- **Normalisation** (Min-Max, Standardisation)
- **Score de qualité** automatique
- **Historique** des traitements par utilisateur
- **Export** CSV, JSON, XML, Excel, PDF

---

## Installation

### 1. Cloner le projet

```bash
git clone <url-du-repo>
cd mon_api
```

### 2. Créer l'environnement virtuel

```bash
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` et remplir :
- `SECRET_KEY` : clé secrète Flask
- `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` : depuis Google Cloud Console

### 5. Configurer Google OAuth

1. Aller sur [Google Cloud Console](https://console.cloud.google.com/)
2. Créer un projet
3. Activer l'API **Google+ API** ou **People API**
4. Aller dans **API & Services > Identifiants > Créer des identifiants > ID client OAuth 2.0**
5. Type d'application : **Application Web**
6. URI de redirection autorisée : `http://localhost:5000/auth/callback`
7. Copier le Client ID et Secret dans `.env`

### 6. Lancer le serveur

```bash
python app.py
```

L'application est disponible sur **http://localhost:5000**

---

## Structure du projet

```
mon_api/
├── app.py                  # Point d'entrée (Flask application factory)
├── config.py               # Configuration (Dev / Prod)
├── models.py               # Modèles SQLAlchemy (User, CleaningHistory, FileMeta)
├── extensions.py           # Extensions Flask (db, login, oauth)
├── requirements.txt
├── Procfile                # Déploiement Render/Heroku
├── .env.example
│
├── routes/
│   ├── auth.py             # Authentification Google OAuth
│   ├── dashboard.py        # Pages web
│   └── api.py              # Endpoints REST (/api/*)
│
├── modules/
│   ├── data_processor.py   # Cœur du traitement des données
│   ├── export_manager.py   # Export CSV/JSON/XML/Excel/PDF
│   └── auth_manager.py     # Logique d'authentification
│
├── templates/
│   ├── base.html           # Layout commun
│   ├── login.html          # Page de connexion
│   ├── dashboard.html      # Interface principale
│   ├── history.html        # Historique
│   └── profile.html        # Profil utilisateur
│
├── static/
│   ├── css/style.css       # Styles
│   └── js/dashboard.js     # Logique frontend
│
├── uploads/                # Fichiers uploadés
├── processed/              # CSV nettoyés
├── reports_out/            # Exports générés
└── database/app.db         # SQLite (auto-créé)
```

---

## Endpoints API

| Méthode | URL | Description |
|---------|-----|-------------|
| POST | `/api/upload` | Uploader un fichier |
| POST | `/api/clean` | Lancer le nettoyage |
| GET  | `/api/export/<id>/<fmt>` | Télécharger l'export |
| GET  | `/api/history` | Historique JSON |
| GET  | `/api/me` | Profil utilisateur |
| GET  | `/auth/login` | Connexion Google |
| GET  | `/auth/callback` | Callback OAuth |
| GET  | `/auth/logout` | Déconnexion |

---

## Déploiement sur Render

1. Créer un compte sur [render.com](https://render.com)
2. Nouveau **Web Service** → connecter le dépôt Git
3. Build Command : `pip install -r requirements.txt`
4. Start Command : `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT`
5. Ajouter les variables d'environnement dans le dashboard Render
6. Mettre à jour l'URI de redirection Google avec l'URL Render

---

## Année universitaire 2025–2026
