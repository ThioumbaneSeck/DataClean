import pandas as pd
import os
import uuid
import json


class ExportManager:
    """Coordinateur d'exports : CSV, JSON, XML, Excel, PDF."""

    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)

    def export(self, fmt: str, output_folder: str) -> str:
        os.makedirs(output_folder, exist_ok=True)
        name = f'export_{uuid.uuid4().hex}'

        if fmt == 'csv':
            return self._to_csv(output_folder, name)
        elif fmt == 'json':
            return self._to_json(output_folder, name)
        elif fmt == 'xml':
            return self._to_xml(output_folder, name)
        elif fmt == 'xlsx':
            return self._to_excel(output_folder, name)
        elif fmt == 'pdf':
            return self._to_pdf(output_folder, name)
        else:
            raise ValueError(f'Format inconnu : {fmt}')

    def _to_csv(self, folder, name):
        path = os.path.join(folder, f'{name}.csv')
        self.df.to_csv(path, index=False)
        return path

    def _to_json(self, folder, name):
        path = os.path.join(folder, f'{name}.json')
        self.df.to_json(path, orient='records', force_ascii=False, indent=2)
        return path

    def _to_xml(self, folder, name):
        path = os.path.join(folder, f'{name}.xml')
        self.df.to_xml(path, index=False)
        return path

    def _to_excel(self, folder, name):
        path = os.path.join(folder, f'{name}.xlsx')
        with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
            self.df.to_excel(writer, index=False, sheet_name='Données nettoyées')
            workbook  = writer.book
            worksheet = writer.sheets['Données nettoyées']
            header_fmt = workbook.add_format({
                'bold': True, 'bg_color': '#1a2235',
                'font_color': '#00e5ff', 'border': 1
            })
            for col_num, col_name in enumerate(self.df.columns):
                worksheet.write(0, col_num, col_name, header_fmt)
                worksheet.set_column(col_num, col_num, max(len(str(col_name)) + 4, 12))
        return path

    def _to_pdf(self, folder, name):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.units import cm
            from datetime import datetime

            path = os.path.join(folder, f'{name}.pdf')
            doc  = SimpleDocTemplate(path, pagesize=A4,
                                     leftMargin=2*cm, rightMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
            styles   = getSampleStyleSheet()
            elements = []

            title_style = ParagraphStyle('Title', parent=styles['Title'],
                                         fontSize=18, textColor=colors.HexColor('#00e5ff'))
            elements.append(Paragraph('Rapport de nettoyage des données', title_style))
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph(
                f'Généré le {datetime.now().strftime("%d/%m/%Y à %H:%M")}',
                styles['Normal']
            ))
            elements.append(Spacer(1, 1*cm))

            # Tableau de données (10 premières lignes)
            preview = self.df.head(10)
            table_data = [list(preview.columns)] + preview.values.tolist()
            tbl = Table(table_data, repeatRows=1)
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a2235')),
                ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor('#00e5ff')),
                ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE',   (0, 0), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(tbl)
            doc.build(elements)
            return path

        except ImportError:
            # Fallback : retourner le CSV si ReportLab n'est pas installé
            return self._to_csv(folder, name)
