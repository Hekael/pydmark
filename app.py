from flask import Flask, render_template, request, jsonify

import pandas as pd
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import io
import base64
import os
import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
DATABASE_URI = 'sqlite:///dmarc_reports.db'

Base = declarative_base()

class DMARCReport(Base):
    __tablename__ = 'dmarc_reports'
    id = Column(Integer, primary_key=True)
    org_name = Column(String)
    email = Column(String)
    report_id = Column(String)
    date_begin = Column(DateTime)
    date_end = Column(DateTime)
    source_ip = Column(String)
    count = Column(Integer)
    disposition = Column(String)
    dkim = Column(String)
    spf = Column(String)
    envelope_to = Column(String, nullable=True)
    envelope_from = Column(String, nullable=True)
    header_from = Column(String)
    dkim_domain = Column(String, nullable=True)
    dkim_selector = Column(String, nullable=True)
    dkim_result = Column(String, nullable=True)
    spf_domain = Column(String, nullable=True)
    spf_scope = Column(String, nullable=True)
    spf_result = Column(String)

engine = create_engine(DATABASE_URI)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

def process_xml(file):
    ''' Parse XML'''
    tree = ET.parse(file)
    root = tree.getroot()

    reports = []

    # pobieranie nagłówka
    metadate = root.find('report_metadata')
    org_name = metadate.find('org_name').text
    email = metadate.find('email').text
    report_id = metadate.find('report_id').text
    date_begin = datetime.datetime.fromtimestamp(int(metadate.find('date_range').find('begin').text))
    date_end = datetime.datetime.fromtimestamp(int(metadate.find('date_range').find('end').text))

    # pobieranie sekcji rekordów
    for record in root.findall('record'):
        row = record.find('row')
        source_ip = row.find('source_ip').text
        count = int(row.find('count').text)
        disposition = row.find('policy_evaluated').find('disposition').text
        dkim = row.find('policy_evaluated').find('dkim').text
        spf = row.find('policy_evaluated').find('spf').text

        identifiers = record.find('identifiers')
        envelope_to = identifiers.find('envelope_to').text if identifiers.find('envelope_to') is not None else None
        envelope_from = identifiers.find('envelope_from').text if identifiers.find('envelope_from') is not None else None
        header_from = identifiers.find('header_from').text

        auth_results = record.find('auth_results')

        dkim_data = auth_results.find('dkim') if auth_results.find('dkim') is not None else None
        dkim_domain = dkim_data.find('domain').text if dkim_data is not None and dkim_data.find('domain') is not None else None
        dkim_selector = dkim_data.find('selector').text if dkim_data is not None and dkim_data.find('selector') is not None else None
        dkim_result = dkim_data.find('result').text if dkim_data is not None and dkim_data.find('result') is not None else None

        spf_data = auth_results.find('spf') if auth_results.find('spf') is not None else None
        spf_domain = spf_data.find('domain').text if spf_data is not None and spf_data.find('domain') is not None else None
        spf_scope = spf_data.find('scope').text if spf_data is not None and spf_data.find('scope') is not None else None
        spf_result = auth_results.find('spf').find('result').text


        report = DMARCReport(
            org_name = org_name,
            email = email,
            report_id = report_id,
            date_begin = date_begin,
            date_end = date_end,
            source_ip = source_ip,
            count = count,
            disposition = disposition,
            dkim = dkim,
            spf = spf,
            envelope_to = envelope_to,
            envelope_from = envelope_from,
            header_from = header_from,
            dkim_domain = dkim_domain,
            dkim_selector = dkim_selector,
            dkim_result = dkim_result,
            spf_domain = spf_domain,
            spf_scope = spf_scope,
            spf_result = spf_result
        )

        reports.append(report)

    session.add_all(reports)
    session.commit()

    #Przenoszenie przetworzonych plików do folderu
    processed_folder_path = os.path.join(PROCESSED_FOLDER, os.path.basename(file))
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    os.rename(file, processed_folder_path)
    print(f"Moved file {file} to {processed_folder_path}")

def generate_plot():
    ''' Generate plot in png'''
    query = session.query(DMARCReport)
    df = pd.read_sql(query.statement, query.session.bind)
    df.set_index('date_begin', inplace=True)
    df = df.resample('D').size()
        
    fig, ax = plt.subplots(figsize=(15, 6)) # Tworzy oś (ax) do rysowania wykresu.
    df.plot(ax=ax) # Rysuje wykres.
    ax.set_title('Number of Reports per Day')
    ax.set_xlabel('Day') # oś x
    ax.set_ylabel('Number of Reports') # oś y

    buf = io.BytesIO() # Tworzy bufor w pamięci.
    plt.savefig(buf, format='png') # Zapisuje wykres do bufora jako obraz PNG.
    buf.seek(0) # Ustawia wskaźnik odczytu na początek bufora.
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8') # Koduje obraz jako base64.
    buf.close() # Zamyka bufor.
    return image_base64

def load_files_from_folder(folder):
    ''' Load all files from uploads and process them into database'''
    for filename in os.listdir(folder):
        if filename.endswith('.xml'):
            file_path = os.path.join(folder, filename)
            try:
                process_xml(file_path)
            except Exception as e:
                print(f"Failed to process file {file_path}: {e}")

def load_data_from_db(offset=0, limit=10, filters=None):
    ''' Load all data from the database into a DataFrame '''
    query = session.query(DMARCReport)

    if filters:
        for column, value in filters.items():
            query = query.filter(getattr(DMARCReport, column).like(f"%{value}%"))

    # Dodaj sortowanie według date_begin malejąco (najnowsze na górze):
    query = query.order_by(DMARCReport.date_begin.desc())

    query = query.offset(offset).limit(limit)
    df = pd.read_sql(query.statement, query.session.bind)
    return df

def calculate_statistics(time_period=None):
    """
    Statystyki dla domen, z możliwością ograniczenia do konkretnego przedziału czasowego.
    time_period może być np. 'week', 'month' lub None (pełne dane).
    """
    query = session.query(DMARCReport)
    df = pd.read_sql(query.statement, query.session.bind)
    
    # Filtrowanie po dacie (jeśli trzeba)
    if time_period == 'day':
        # Poprzedni dzień
        since = datetime.datetime.now() - datetime.timedelta(days=2)
        df = df[df['date_begin'] >= since]
    elif time_period == 'week':
        since = datetime.datetime.now() - datetime.timedelta(days=7)
        df = df[df['date_begin'] >= since]
    elif time_period == 'month':
        since = datetime.datetime.now() - datetime.timedelta(days=30)
        df = df[df['date_begin'] >= since]

    # Usuń wiersze, gdzie header_from jest None:
    df = df.dropna(subset=['header_from'])
    # Pobranie unikalnych domen i posortowanie alfabetycznie
    domains = sorted(df['header_from'].unique())

    stats = {}
    
    for domain in domains:
        domain_data = df[df['header_from'] == domain]
        total_count = domain_data['count'].astype(int).sum()
        delivered_count = domain_data[domain_data['disposition'] == 'none']['count'].astype(int).sum()
        rejected_count = domain_data[domain_data['disposition'] == 'reject']['count'].astype(int).sum()

        delivered_percentage = round((delivered_count / total_count) * 100, 2) if total_count > 0 else 0
        rejected_percentage = round((rejected_count / total_count) * 100, 2) if total_count > 0 else 0

        stats[domain] = {
            'total_count': total_count,
            'delivered_count': delivered_count,
            'rejected_count': rejected_count,
            'delivered_percentage': delivered_percentage,
            'rejected_percentage': rejected_percentage
        }
    
    return stats

@app.route('/', methods=['GET'])
def index():
    ''' Render HTML'''
    load_files_from_folder(UPLOAD_FOLDER)
    plot_url = generate_plot()
    
    # Statystyki za ostatni dzień
    stats_day = calculate_statistics(time_period='day')
    # Statystyki za ostatni tydzień
    stats_week = calculate_statistics(time_period='week')
    # Statystyki za ostatni miesiąc
    stats_month = calculate_statistics(time_period='month')
    # Pełne statystyki (to, co wcześniej)
    stats_all = calculate_statistics(time_period=None)
    
    return render_template(
        'index.html', 
        plot_url=plot_url, 
        stats_day=stats_day,
        stats_week=stats_week, 
        stats_month=stats_month, 
        stats_all=stats_all
    )

@app.route('/api/data', methods=['GET'])
def api_data():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))
    filters = {key: value for key, value in request.args.items() if key not in ['offset', 'limit']}
    data = load_data_from_db(offset=offset, limit=limit, filters=filters)
    return data.to_json(orient='records')

if __name__ == '__main__':
    app.run(debug=True)
