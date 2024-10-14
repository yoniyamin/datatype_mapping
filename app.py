# app.py
import gunicorn
from flask import Flask, render_template, jsonify, request
from bs4 import BeautifulSoup
import requests
import json
import os

app = Flask(__name__)


# Original mapping extraction from URL (updated)
def extract_mapping_from_page(url):
    response = requests.get(url)

    if response.headers['Content-Type'].startswith('text/html'):
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        mappings = []

        if table:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip the header row
                cols = row.find_all('td')
                if len(cols) >= 2:
                    source_or_replicate_type = cols[0].text.strip()
                    replicate_or_target_type = cols[1].text.strip()
                    mappings.append({
                        "source_or_replicate_type": source_or_replicate_type,
                        "replicate_or_target_type": replicate_or_target_type
                    })

        return mappings
    else:
        return {"error": "Invalid content type. Please provide a valid URL to the documentation page."}


# Original file-reading logic
def read_urls_from_file(filename):
    if not os.path.exists(filename):
        print(f"Error: {filename} not found.")
        return []

    with open(filename, 'r') as f:
        urls = []
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 1:
                urls.append((parts[0], "Unknown", parts[0]))  # If only URL is provided, use "Unknown" as DB type
            elif len(parts) >= 2:
                urls.append((parts[0], parts[1], parts[0]))  # Use first two parts as URL and DB type, and URL again
        return urls


# Update the mappings.json file
def update_mappings():
    sources_urls = read_urls_from_file('urls_sources.txt')
    targets_urls = read_urls_from_file('urls_targets.txt')

    mappings = {
        "sources": {},
        "targets": {}
    }

    for url, db_type, original_url in sources_urls:
        data = extract_mapping_from_page(url)
        if isinstance(data, list):
            mappings["sources"][db_type] = {"data_types": data, "url": original_url}
            print(f"Scraping {url} was done successfully, {db_type} will be included in the source list.")
        else:
            print(f"Error processing source {url}: {data.get('error', 'Unknown error')}")

    print(f"Scraping of source databases is now completed.")

    for url, db_type, original_url in targets_urls:
        data = extract_mapping_from_page(url)
        if isinstance(data, list):
            mappings["targets"][db_type] = {"data_types": data, "url": original_url}
            print(f"Scraping {url} was done successfully, {db_type} will be included in the target list.")
        else:
            print(f"Error processing target {url}: {data.get('error', 'Unknown error')}")

    print(f"Scraping of target databases is now completed.")
    with open('mappings.json', 'w') as f:
        json.dump(mappings, f, indent=2)


# Route for the main page
@app.route('/')
def index():
    with open('mappings.json', 'r') as f:
        mappings = json.load(f)
    sources = list(mappings['sources'].keys())
    targets = list(mappings['targets'].keys())
    return render_template('index.html', sources=sources, targets=targets)


# API route to get mappings
@app.route('/api/mappings')
def get_mappings():
    with open('mappings.json', 'r') as f:
        mappings = json.load(f)
    return jsonify(mappings)


# Route to get combined table data
@app.route('/api/combined_table')
def get_combined_table():
    source = request.args.get('source')
    target = request.args.get('target')

    with open('mappings.json', 'r') as f:
        mappings = json.load(f)

    source_data = mappings['sources'].get(source, {})
    target_data = mappings['targets'].get(target, {})

    combined_data = []
    for source_type in source_data.get('data_types', []):
        combined_row = {
            'source_type': source_type['source_or_replicate_type'],
            'replicate_type': source_type['replicate_or_target_type'],
            'target_type': 'N/A'
        }
        normalized_replicate_type = source_type['replicate_or_target_type'].split(' ')[0].upper()

        for target_type in target_data.get('data_types', []):
            normalized_target_type = target_type['source_or_replicate_type'].split(' ')[0].upper()

            if normalized_replicate_type in normalized_target_type or normalized_target_type in normalized_replicate_type:
                combined_row['target_type'] = target_type['replicate_or_target_type']
                break

        combined_data.append(combined_row)

    return jsonify({
        'table_data': combined_data,
        'source_url': source_data.get('url', ''),
        'target_url': target_data.get('url', '')
    })


# New route to rescrape URLs and return the combined table data
@app.route('/api/update_mappings_and_get_combined_table')
def update_mappings_and_get_combined_table():
    source = request.args.get('source')
    target = request.args.get('target')

    # Rescrape the URLs
    update_mappings()

    # Load the updated mappings
    with open('mappings.json', 'r') as f:
        mappings = json.load(f)

    source_data = mappings['sources'].get(source, {})
    target_data = mappings['targets'].get(target, {})

    combined_data = []
    for source_type in source_data.get('data_types', []):
        combined_row = {
            'source_type': source_type['source_or_replicate_type'],
            'replicate_type': source_type['replicate_or_target_type'],
            'target_type': 'N/A'
        }
        normalized_replicate_type = source_type['replicate_or_target_type'].split(' ')[0].upper()

        for target_type in target_data.get('data_types', []):
            normalized_target_type = target_type['source_or_replicate_type'].split(' ')[0].upper()

            if normalized_replicate_type in normalized_target_type or normalized_target_type in normalized_replicate_type:
                combined_row['target_type'] = target_type['replicate_or_target_type']
                break

        combined_data.append(combined_row)

    return jsonify({
        'table_data': combined_data,
        'source_url': source_data.get('url', ''),
        'target_url': target_data.get('url', '')
    })


if __name__ == '__main__':
    app.run(debug=True)
