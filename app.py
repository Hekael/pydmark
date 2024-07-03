from flask import Flask, request, render_template
import pandas as pd
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

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
    date_begin = metadate.find('date_range').find('begin').text
    date_end = metadate.find('date_range').find('end').text

    # pobieranie sekcji rekordów
    for record in root.findall('record'):
        row = record.find('row')
        source_ip = row.find('source_ip').text
        count = row.find('count').text
        dispositon = row.find('policy_evaluated').find('disposition').text
        dkim = row.find('policy_evaluated').find('dkim').text
        spf = row.find('policy_evaluated').find('spf').text

        identifiers = record.find('identifiers')
        envelope_to = identifiers.find('envelope_to').text
        envelope_from = identifiers.find('envelope_from').text
        header_from = identifiers.find('header_from').text

        auth_results = record.find('auth_results')
        dkim_domain = auth_results.find('dkim').find('domain').text
        dkim_selector = auth_results.find('dkim').find('selector').text
        dkim_result = auth_results.find('dkim').find('result').text

        spf_domain = auth_results.find('spf').find('domain').text
        spf_scope = auth_results.find('spf').find('scope').text
        spf_result = auth_results.find('spf').find('result').text

        reports.append({
            'org_name': org_name,
            'email': email,
            'report_id': report_id,
            'date_begin': date_begin,
            'date_end': date_end,
            'source_ip': source_ip,
            'count': count,
            'dispositon': dispositon,
            'dkim': dkim,
            'spf': spf,
            'envelope_to': envelope_to,
            'envelope_from': envelope_from,
            'header_from': header_from,
            'dkim_domain': dkim_domain,
            'dkim_selector': dkim_selector,
            'dkim_result': dkim_result,
            'spf_domain': spf_domain,
            'spf_scope': spf_scope,
            'spf_result': spf_result
        })

    return pd.DataFrame(reports)

def generate_plot(data):
    ''' Generate plot in png'''
    _, ax = plt.subplots() # Tworzy oś (ax) do rysowania wykresu.
    data['date_begin'] = pd.to_datetime(data['date_begin'], unit='s') # Konwertuje kolumnę 'date' na typ datetime.
    data.set_index('date_begin').resample('D').size().plot(ax=ax) # ResaDpluje dane i rysuje wykres.
    ax.set_title('Number of Reports per Month')
    ax.set_xlabel('Day') # oś x
    ax.set_ylabel('Number of Reports') # oś y

    buf = io.BytesIO() # Tworzy bufor w pamięci.
    plt.savefig(buf, format='png') # Zapisuje wykres do bufora jako obraz PNG.
    buf.seek(0) # Ustawia wskaźnik odczytu na początek bufora.
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8') # Koduje obraz jako base64.
    buf.close() # Zamyka bufor.
    return image_base64

@app.route('/', methods=['GET','POST'])
def index():
    ''' Render HTML'''
    if request.method == 'POST':
        files = request.files.getlist('files')
        all_data = pd.DataFrame()

        for file in files:
            data = process_xml(file)
            all_data = pd.concat([all_data, data], ignore_index=True)

        plot_url = generate_plot(all_data)
        return render_template('index.html', plot_url=plot_url, tabels=[all_data.to_html(classes='data')])
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)