# app.py
import gunicorn
from flask import Flask, render_template, jsonify, request
from bs4 import BeautifulSoup
import requests
import json
import os
from advancedParsing import AdvancedMappingParser, process_database_mappings

app = Flask(__name__)

scraping_progress = {"progress": 0}  # Global variable to store scraping progress

@app.route('/api/scraping_progress')
def get_scraping_progress():
    return jsonify(scraping_progress)

def normalize_type(data_type):
    return data_type.split('(')[0].strip().upper()

def process_complex_mapping(data_type, rules):
    """
    Process complex data type mappings into multiple entries based on rules.

    :param data_type: The original data type (e.g., "NUMBER").
    :param rules: A list of rules defining the conditions and mappings.
    :return: A list of individual mappings.
    """
    mappings = []
    for rule in rules:
        condition = rule.get("condition", "")
        replicate_type = rule.get("replicate_type", "")
        source_type = f"{data_type}({condition})" if condition else data_type
        mappings.append({
            "source_or_replicate_type": source_type,
            "replicate_or_target_type": replicate_type
        })
    return mappings

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

                    # Handle specific complex cases
                    if source_or_replicate_type == "NUMBER(P,S)":
                        rules = [
                            {"condition": "scale < 0", "replicate_type": "REAL8"},
                            {"condition": "scale = 0 and precision = 0", "replicate_type": "REAL8"},
                            {"condition": "scale = 0 and precision <= 2", "replicate_type": "INT1"},
                            {"condition": "scale = 0 and precision > 2 and precision <= 4", "replicate_type": "INT2"},
                            {"condition": "scale = 0 and precision > 4 and precision <= 9", "replicate_type": "INT4"},
                            {"condition": "scale = 0 and precision > 9", "replicate_type": "NUMERIC"},
                            {"condition": "all other cases", "replicate_type": "REAL8"}
                        ]
                        mappings.extend(process_complex_mapping("NUMBER", rules))
                    elif source_or_replicate_type == "VARCHAR2":
                        rules = [
                            {"condition": "Length <= 4000 bytes", "replicate_type": "STRING"},
                            {"condition": "Length > 4000 bytes", "replicate_type": "CLOB"}
                        ]
                        mappings.extend(process_complex_mapping("VARCHAR2", rules))
                    else:
                        mappings.append({
                            "source_or_replicate_type": source_or_replicate_type,
                            "replicate_or_target_type": replicate_or_target_type  # Fixed here
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
    global scraping_progress
    sources_urls = read_urls_from_file('urls_sources.txt')
    targets_urls = read_urls_from_file('urls_targets.txt')

    mappings = {
        "sources": {},
        "targets": {}
    }

    total_tasks = len(sources_urls) + len(targets_urls)
    completed_tasks = 0

    for url, db_type, original_url in sources_urls:
        data = extract_mapping_from_page(url)
        if isinstance(data, list):
            mappings["sources"][db_type] = {"data_types": data, "url": original_url}
        completed_tasks += 1
        scraping_progress["progress"] = int((completed_tasks / total_tasks) * 100)

    for url, db_type, original_url in targets_urls:
        data = extract_mapping_from_page(url)
        if isinstance(data, list):
            mappings["targets"][db_type] = {"data_types": data, "url": original_url}
        completed_tasks += 1
        scraping_progress["progress"] = int((completed_tasks / total_tasks) * 100)

    with open('mappings.json', 'w') as f:
        json.dump(mappings, f, indent=2)

    scraping_progress["progress"] = 100

def update_mappings_specific(source=None, target=None):
    """
    Scrape and update mappings for specific source and target databases.
    """
    sources_urls = read_urls_from_file('urls_sources.txt')
    targets_urls = read_urls_from_file('urls_targets.txt')

    # Load existing mappings
    if os.path.exists('mappings.json'):
        with open('mappings.json', 'r') as f:
            mappings = json.load(f)
    else:
        mappings = {"sources": {}, "targets": {}}

    # Scrape specific source database
    if source:
        for url, db_type, original_url in sources_urls:
            if db_type == source:
                data = extract_mapping_from_page(url)
                if isinstance(data, list):
                    mappings["sources"][db_type] = {"data_types": data, "url": original_url}
                    print(f"Scraping {url} succeeded. {db_type} updated in sources.")
                else:
                    print(f"Error processing source {url}: {data.get('error', 'Unknown error')}")

    # Scrape specific target database
    if target:
        for url, db_type, original_url in targets_urls:
            if db_type == target:
                data = extract_mapping_from_page(url)
                if isinstance(data, list):
                    mappings["targets"][db_type] = {"data_types": data, "url": original_url}
                    print(f"Scraping {url} succeeded. {db_type} updated in targets.")
                else:
                    print(f"Error processing target {url}: {data.get('error', 'Unknown error')}")

    # Save updated mappings
    with open('mappings.json', 'w') as f:
        json.dump(mappings, f, indent=2)
    print("Specific mapping update completed.")

def match_target_type(replicate_type, target_mappings):
    """
    Match replicate type with target mappings using fallback logic.
    """
    replicate_type = replicate_type.lower()
    for target_entry in target_mappings:
        target_type = target_entry.get('source_or_replicate_type', '').lower()
        if replicate_type == target_type:
            return target_entry.get('replicate_or_target_type', 'N/A')

    return 'N/A'


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


@app.route('/api/combined_table')
def get_combined_table():
    """
    Combine source and target mappings into a table with optional advanced parsing.
    """
    source = request.args.get('source')
    target = request.args.get('target')
    remapping_option = request.args.get('remapping_option', 'existing')
    use_advanced = request.args.get('use_advanced', 'false').lower() == 'true'

    # Handle remapping logic
    if remapping_option == "all":
        update_mappings()
    elif remapping_option == "selected":
        update_mappings_specific(source, target)

    # Load mappings
    with open('mappings.json', 'r') as f:
        mappings = json.load(f)

    source_data = mappings['sources'].get(source, {})
    target_data = mappings['targets'].get(target, {})

    # Use advanced parsing if the flag is enabled
    if use_advanced:
        combined_data = process_database_mappings(source_data, target_data)
    else:
        combined_data = []
        for source_entry in source_data.get('data_types', []):
            replicate_type = normalize_type(source_entry['replicate_or_target_type'])
            combined_row = {
                'source_type': source_entry['source_or_replicate_type'],
                'replicate_type': replicate_type,
                'target_type': match_target_type(replicate_type, target_data.get('data_types', []))
            }
            combined_data.append(combined_row)

    return jsonify({
        'table_data': combined_data,
        'source_url': source_data.get('url', ''),
        'target_url': target_data.get('url', '')
    })


if __name__ == '__main__':
    app.run(debug=True)
