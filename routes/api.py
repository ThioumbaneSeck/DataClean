from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models import CleaningHistory, FileMeta, User
from modules.data_processor import DataProcessor
from modules.export_manager import ExportManager
import os, uuid, hashlib, math
from datetime import datetime
import pandas as pd
import json

api_bp = Blueprint('api', __name__)


def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS'])


def md5_file(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def sanitize(obj):
    """Remplace NaN/Inf par None récursivement."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


# ─── Upload ──────────────────────────────────────────────────────────────────

@api_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400

    f = request.files['file']
    if not f.filename or not allowed_file(f.filename):
        return jsonify({'error': 'Format non supporté (csv, xlsx, json, xml)'}), 400

    filename    = secure_filename(f.filename)
    stored_name = f'{uuid.uuid4().hex}_{filename}'
    path        = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name)
    f.save(path)

    # Déduplication par hash MD5
    file_hash = md5_file(path)
    existing  = FileMeta.query.filter_by(user_id=current_user.id, file_hash=file_hash).first()
    if existing:
        os.remove(path)
        return jsonify({'warning': 'Fichier déjà traité', 'file_id': existing.id}), 200

    meta = FileMeta(
        user_id       = current_user.id,
        original_name = filename,
        stored_name   = stored_name,
        file_path     = path,
        file_hash     = file_hash,
        file_size     = os.path.getsize(path),
        mime_type     = f.content_type,
    )
    db.session.add(meta)
    db.session.commit()
    return jsonify({'file_id': meta.id, 'filename': filename, 'size': meta.file_size}), 200


# ─── Nettoyage ───────────────────────────────────────────────────────────────

@api_bp.route('/clean', methods=['POST'])
@login_required
def clean():
    data    = request.get_json()
    file_id = data.get('file_id')
    opts    = data.get('options', {})

    meta = FileMeta.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not meta:
        return jsonify({'error': 'Fichier introuvable'}), 404

    try:
        meta.status = 'processing'
        db.session.commit()

        processor = DataProcessor(meta.file_path)
        result    = processor.run(
            remove_duplicates = opts.get('duplicates', True),
            handle_missing    = opts.get('missing', True),
            missing_method    = opts.get('missing_method', 'mean'),
            handle_outliers   = opts.get('outliers', True),
            outlier_method    = opts.get('outlier_method', 'iqr'),
            normalize         = opts.get('normalize', True),
            norm_method       = opts.get('norm_method', 'minmax'),
        )

        # Sauvegarde CSV nettoyé
        output_name = f'cleaned_{uuid.uuid4().hex}.csv'
        output_path = os.path.join(current_app.config['PROCESSED_FOLDER'], output_name)
        result['dataframe'].to_csv(output_path, index=False)

        # Enregistrement historique
        stats = result['stats']
        hist  = CleaningHistory(
            user_id              = current_user.id,
            file_name            = meta.original_name,
            original_rows        = stats['initial_rows'],
            cleaned_rows         = stats['final_rows'],
            original_cols        = stats['initial_cols'],
            duplicates_removed   = stats['duplicates_removed'],
            missing_treated      = stats['missing_treated'],
            outliers_treated     = stats['outliers_treated'],
            missing_method       = opts.get('missing_method', 'mean'),
            outlier_method       = opts.get('outlier_method', 'iqr'),
            normalization_method = opts.get('norm_method', 'minmax'),
            quality_score        = stats['quality_score'],
            output_path          = output_path,
        )
        hist.stats = sanitize(stats)
        db.session.add(hist)

        # Mise à jour compteurs utilisateur
        current_user.total_cleanings    += 1
        current_user.total_rows_cleaned += stats['final_rows']
        meta.status = 'done'
        db.session.commit()

        return jsonify({
            'history_id'   : hist.id,
            'stats'        : sanitize(stats),
            'quality_score': sanitize(stats['quality_score']),
            'preview'      : sanitize(result['preview']),
        }), 200

    except Exception as e:
        meta.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


# ─── Export ──────────────────────────────────────────────────────────────────

@api_bp.route('/export/<int:history_id>/<fmt>', methods=['GET'])
@login_required
def export(history_id, fmt):
    hist = CleaningHistory.query.filter_by(id=history_id, user_id=current_user.id).first()
    if not hist or not hist.output_path:
        return jsonify({'error': 'Données introuvables'}), 404

    try:
        manager  = ExportManager(hist.output_path)
        out_path = manager.export(fmt, current_app.config['REPORTS_FOLDER'])
        mime_map = {
            'csv' : 'text/csv',
            'json': 'application/json',
            'xml' : 'application/xml',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf' : 'application/pdf',
        }
        return send_file(out_path, mimetype=mime_map.get(fmt, 'application/octet-stream'),
                         as_attachment=True,
                         download_name=f'cleaned_data_{history_id}.{fmt}')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Historique ──────────────────────────────────────────────────────────────

@api_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    records = (CleaningHistory.query
               .filter_by(user_id=current_user.id)
               .order_by(CleaningHistory.created_at.desc())
               .limit(50).all())
    return jsonify([{
        'id'           : h.id,
        'file_name'    : h.file_name,
        'original_rows': h.original_rows,
        'cleaned_rows' : h.cleaned_rows,
        'quality_score': sanitize(h.quality_score),
        'created_at'   : h.created_at.isoformat(),
    } for h in records])


# ─── Profil ──────────────────────────────────────────────────────────────────

@api_bp.route('/me', methods=['GET'])
@login_required
def me():
    return jsonify({
        'id'             : current_user.id,
        'email'          : current_user.email,
        'name'           : current_user.name,
        'picture'        : current_user.picture,
        'total_cleanings': current_user.total_cleanings,
        'total_rows'     : current_user.total_rows_cleaned,
        'is_admin'       : current_user.is_admin,
    })


# ─── Analyse pré-traitement ──────────────────────────────────────────────────

@api_bp.route('/analyze', methods=['POST'])
@login_required
def analyze_file():

    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'Fichier invalide'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in current_app.config.get('ALLOWED_EXTENSIONS', {'csv', 'xlsx', 'xls', 'json', 'xml'}):
        return jsonify({'error': f'Format .{ext} non supporté'}), 400

    try:
        # ── Chargement selon le format ──────────────────────────────────────
        if ext == 'csv':
            df = pd.read_csv(file)
        elif ext in ('xlsx', 'xls'):
            df = pd.read_excel(file)
        elif ext == 'json':
            raw = json.loads(file.read().decode('utf-8'))
            if isinstance(raw, list):
                df = pd.DataFrame(raw)
            elif isinstance(raw, dict):
                list_key = next((k for k, v in raw.items() if isinstance(v, list)), None)
                df = pd.DataFrame(raw[list_key]) if list_key else pd.json_normalize(raw)
            else:
                return jsonify({'error': 'Structure JSON non supportée'}), 400
        elif ext == 'xml':
            df = pd.read_xml(file)
        else:
            return jsonify({'error': 'Format non supporté'}), 400

        if df.empty:
            return jsonify({'error': 'Le fichier est vide'}), 400

        rows, cols = df.shape

        # ── Fonction sanitize locale ────────────────────────────────────────
        def _sanitize(obj):
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_sanitize(v) for v in obj]
            if isinstance(obj, float) and (obj != obj or obj in (float('inf'), float('-inf'))):
                return None
            if hasattr(obj, 'item'):   # types numpy → Python natif
                return obj.item()
            return obj

        # ── 1. Infos générales ──────────────────────────────────────────────
        col_types = {col: str(dtype) for col, dtype in df.dtypes.items()}

        # ── 2. Valeurs manquantes ───────────────────────────────────────────
        missing_counts = df.isnull().sum()
        missing_pct    = (missing_counts / rows * 100).round(2)
        missing_info   = [
            {
                'column' : col,
                'missing': int(missing_counts[col]),
                'pct'    : float(missing_pct[col])
            }
            for col in df.columns if missing_counts[col] > 0
        ]

        # ── 3. Statistiques descriptives (colonnes numériques) ──────────────
        num_df = df.select_dtypes(include='number')
        desc   = num_df.describe().to_dict() if not num_df.empty else {}
        desc_clean = _sanitize(desc)

        stats_by_col = {}
        for stat_name, col_dict in desc_clean.items():
            for col_name, value in col_dict.items():
                if col_name not in stats_by_col:
                    stats_by_col[col_name] = {}
                stats_by_col[col_name][stat_name] = value

        # ── 4. Détection des outliers (méthode IQR) ─────────────────────────
        outliers_info = []
        for col in num_df.columns:
            series  = num_df[col].dropna()
            if len(series) < 4:
                continue
            Q1  = series.quantile(0.25)
            Q3  = series.quantile(0.75)
            IQR = Q3 - Q1
            if IQR == 0:
                continue
            lower  = Q1 - 1.5 * IQR
            upper  = Q3 + 1.5 * IQR
            mask   = (series < lower) | (series > upper)
            count  = int(mask.sum())
            if count > 0:
                outliers_info.append({
                    'column' : col,
                    'count'  : count,
                    'pct'    : round(count / len(series) * 100, 2),
                    'lower'  : round(float(lower), 4),
                    'upper'  : round(float(upper), 4),
                    'min_val': round(float(series[mask].min()), 4),
                    'max_val': round(float(series[mask].max()), 4),
                })

        # ── 5. Aperçu (5 premières lignes) ─────────────────────────────────
        preview_df   = df.head(5).where(df.head(5).notna(), None)
        preview_rows = _sanitize(preview_df.to_dict(orient='records'))

        # ── 6. Doublons ─────────────────────────────────────────────────────
        duplicate_count = int(df.duplicated().sum())

        return jsonify({
            'success': True,
            'info': {
                'rows'      : rows,
                'cols'      : cols,
                'columns'   : list(df.columns),
                'col_types' : col_types,
                'duplicates': duplicate_count,
                'file_name' : file.filename,
                'extension' : ext,
            },
            'missing' : missing_info,
            'outliers': outliers_info,       
            'stats'   : stats_by_col,
            'preview' : preview_rows,
        })

    except Exception as e:
        current_app.logger.error(f'Erreur analyse : {e}')
        return jsonify({'error': f'Erreur lors de l\'analyse : {str(e)}'}), 500
