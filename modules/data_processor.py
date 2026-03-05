import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
import os
import json


class DataProcessor:
    """
    Cœur du traitement des données.
    Prend en charge CSV, Excel, JSON, XML.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.df        = self._load()
        self._clean_index_columns()
        self.stats = {
            'initial_rows'     : len(self.df),
            'initial_cols'     : len(self.df.columns),
            'final_rows'       : 0,
            'final_cols'       : 0,
            'duplicates_removed': 0,
            'missing_treated'  : 0,
            'outliers_treated' : 0,
            'quality_score'    : 0.0,
        }

    # ── Chargement ────────────────────────────────────────────────────────────

    def _load(self) -> pd.DataFrame:
        ext = os.path.splitext(self.file_path)[1].lower()

        if ext == '.json':
            return self._load_json()

        loaders = {
            '.csv' : lambda p: pd.read_csv(p),
            '.xlsx': lambda p: pd.read_excel(p),
            '.xls' : lambda p: pd.read_excel(p),
            '.xml' : lambda p: pd.read_xml(p),
        }
        loader = loaders.get(ext)
        if loader is None:
            raise ValueError(f'Format non supporté : {ext}')
        return loader(self.file_path)

    def _load_json(self) -> pd.DataFrame:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content:
            raise ValueError("Le fichier JSON est vide")

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Fichier JSON invalide : {e}")

        # Cas 1 : liste de dicts → format tabulaire standard
        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError("Le fichier JSON contient une liste vide")
            return pd.json_normalize(data)

        # Cas 2 : dict avec une clé contenant une liste
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    return pd.json_normalize(value)

            # Cas 3 : dict simple → aplatir en une ligne
            return pd.json_normalize(data)

        raise ValueError("Structure JSON non supportée pour le traitement tabulaire")

    # ── Nettoyage colonnes index parasites ───────────────────────────────────

    def _clean_index_columns(self):
        to_drop = []
        for col in self.df.columns:
            if str(col).startswith('Unnamed') or str(col).lower() == 'index':
                to_drop.append(col)
            elif pd.api.types.is_numeric_dtype(self.df[col]):
                if list(self.df[col]) == list(range(len(self.df))):
                    to_drop.append(col)
        if to_drop:
            self.df.drop(columns=to_drop, inplace=True)

    # ── Pipeline principal ───────────────────────────────────────────────────

    def run(self,
            remove_duplicates: bool = True,
            handle_missing   : bool = True,
            missing_method   : str  = 'mean',
            handle_outliers  : bool = True,
            outlier_method   : str  = 'iqr',
            normalize        : bool = False,
            norm_method      : str  = 'minmax') -> dict:

        if remove_duplicates:
            self._remove_duplicates()

        if handle_missing:
            self._handle_missing(missing_method)

        if handle_outliers:
            self._handle_outliers(outlier_method)

        if normalize:
            self._normalize(norm_method)

        self.stats['final_rows']    = len(self.df)
        self.stats['final_cols']    = len(self.df.columns)
        self.stats['quality_score'] = self._compute_quality_score()

        # Convertir les types numpy en types Python natifs avant to_dict
        preview_df = self.df.head(10).copy()
        for col in preview_df.columns:
            if pd.api.types.is_integer_dtype(preview_df[col]):
                preview_df[col] = preview_df[col].astype(object)
            elif pd.api.types.is_float_dtype(preview_df[col]):
                preview_df[col] = preview_df[col].astype(object)

        return {
            'dataframe': self.df,
            'stats'    : self.stats,
            'preview'  : preview_df.where(preview_df.notna(), None).to_dict(orient='records'),
        }

    # ── Suppression des doublons ──────────────────────────────────────────────

    def _remove_duplicates(self):
        before = len(self.df)
        self.df.drop_duplicates(inplace=True)
        self.df.reset_index(drop=True, inplace=True)
        self.stats['duplicates_removed'] = before - len(self.df)

    # ── Valeurs manquantes ────────────────────────────────────────────────────

    def _handle_missing(self, method: str):
        count = int(self.df.isnull().sum().sum())
        if method == 'drop':
            self.df.dropna(inplace=True)
            self.df.reset_index(drop=True, inplace=True)
        else:
            num_cols = self.df.select_dtypes(include=[np.number]).columns
            cat_cols = self.df.select_dtypes(exclude=[np.number]).columns

            for col in num_cols:
                if self.df[col].isnull().any():
                    if method == 'mean':
                        self.df[col].fillna(self.df[col].mean(), inplace=True)
                    elif method == 'median':
                        self.df[col].fillna(self.df[col].median(), inplace=True)
                    elif method == 'mode':
                        self.df[col].fillna(self.df[col].mode()[0], inplace=True)

            for col in cat_cols:
                if self.df[col].isnull().any():
                    mode_val = self.df[col].mode()
                    self.df[col].fillna(mode_val[0] if len(mode_val) > 0 else 'N/A', inplace=True)

        self.stats['missing_treated'] = count

    # ── Outliers ──────────────────────────────────────────────────────────────

    def _handle_outliers(self, method: str):
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        total    = 0

        for col in num_cols:
            if method == 'iqr':
                q1, q3 = self.df[col].quantile(0.25), self.df[col].quantile(0.75)
                iqr    = q3 - q1
                mask   = (self.df[col] < q1 - 1.5 * iqr) | (self.df[col] > q3 + 1.5 * iqr)
            elif method == 'zscore':
                z    = np.abs(scipy_stats.zscore(self.df[col].dropna()))
                idx  = self.df[col].dropna().index
                mask = pd.Series(False, index=self.df.index)
                mask[idx] = z > 3
            else:
                continue

            count = int(mask.sum())
            if count > 0:
                median_val = self.df[col].median()
                self.df.loc[mask, col] = median_val
                total += count

        self.stats['outliers_treated'] = total

    # ── Normalisation ─────────────────────────────────────────────────────────

    def _normalize(self, method: str):
        num_cols = self.df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            col_min, col_max = self.df[col].min(), self.df[col].max()
            if method == 'minmax':
                if col_max != col_min:
                    self.df[col] = (self.df[col] - col_min) / (col_max - col_min)
            elif method == 'standard':
                std = self.df[col].std()
                if std != 0:
                    self.df[col] = (self.df[col] - self.df[col].mean()) / std
            self.df[col] = self.df[col].round(4)

    # ── Score de qualité ──────────────────────────────────────────────────────

    def _compute_quality_score(self) -> float:
        total_cells  = self.df.size
        null_cells   = int(self.df.isnull().sum().sum())
        completeness = (1 - null_cells / total_cells) if total_cells > 0 else 1.0
        dup_penalty  = min(self.stats['duplicates_removed'] / max(self.stats['initial_rows'], 1), 0.3)
        score        = round((completeness * 0.7 + (1 - dup_penalty) * 0.3) * 100, 1)
        return min(score, 99.0)