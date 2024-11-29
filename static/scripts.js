document.getElementById('generate-table').addEventListener('click', function () {
    const source = document.getElementById('source-select').value;
    const target = document.getElementById('target-select').value;
    const useAdvanced = document.getElementById('use-advanced')?.checked; // Checkbox for advanced parsing
    const remappingOption = document.querySelector('input[name="remapping-option"]:checked')?.value || 'existing';

    if (!source || !target) {
        alert('Please select both source and target.');
        return;
    }

    const exportButton = document.getElementById('export-csv');
    exportButton.style.display = 'none';

    // Show progress bar
    startProgressBar();

    // Fetch combined table data
    fetch(`/api/combined_table?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}&use_advanced=${useAdvanced}&remapping_option=${remappingOption}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('API response:', data);

            // Populate the table
            renderTable(data.table_data);

            // Make the Export to CSV button visible
            exportButton.style.display = 'inline-block';

            // Update the references
            if (data.source_url || data.target_url) {
                const urlLinksHtml = `
                    <h3>References</h3>
                    <p><a href="${data.source_url}" target="_blank">Source Documentation</a></p>
                    <p><a href="${data.target_url}" target="_blank">Target Documentation</a></p>
                `;
                document.getElementById('url-links').innerHTML = urlLinksHtml;
            } else {
                document.getElementById('url-links').innerHTML = '<p>No documentation links available.</p>';
            }

            // Stop the progress bar
            stopProgressBar();
        })
        .catch(error => {
            console.error('Error fetching combined table:', error);
            alert(`An error occurred while generating the table: ${error.message}. Please check the console for details.`);
            stopProgressBar();
        });
});

document.getElementById('export-csv').addEventListener('click', function () {
    const source = document.getElementById('source-select').value;
    const target = document.getElementById('target-select').value;

    if (!source || !target) {
        alert('Please generate a table first before exporting to CSV.');
        return;
    }

    exportToCSV(source, target);
});

function startProgressBar() {
    const progressBarContainer = document.getElementById('progress-bar-container');
    const progressBarFill = document.getElementById('progress-bar-fill');

    if (progressBarContainer && progressBarFill) {
        progressBarContainer.style.display = 'block'; // Show progress bar
        progressBarFill.style.width = '0%';
        progressBarFill.innerText = 'Loading...';
    }
}

function stopProgressBar() {
    const progressBarContainer = document.getElementById('progress-bar-container');
    const progressBarFill = document.getElementById('progress-bar-fill');

    if (progressBarContainer && progressBarFill) {
        progressBarFill.style.width = '100%';
        progressBarFill.innerText = 'Complete';
        setTimeout(() => {
            progressBarContainer.style.display = 'none';
        }, 500); // Delay hiding to show "Complete" briefly
    }
}

function renderTable(data) {
    const tableContainer = document.getElementById('table-container');
    if (!data.length) {
        tableContainer.innerHTML = "<p>No mappings found.</p>";
        return;
    }

    let tableHtml = `
        <table class="table">
            <thead>
                <tr>
                    <th>Source Datatype</th>
                    <th>Replicate Datatype</th>
                    <th>Target Datatype</th>
                </tr>
            </thead>
            <tbody>
    `;

    data.forEach(row => {
        tableHtml += `
            <tr>
                <td>${row.source_type || "N/A"}</td>
                <td>${row.replicate_type || "N/A"}</td>
                <td>${row.target_type || "N/A"}</td>
            </tr>
        `;
    });

    tableHtml += `
            </tbody>
        </table>
    `;

    tableContainer.innerHTML = tableHtml;
}

function exportToCSV(source, target) {
    const table = document.getElementById('table-container');
    if (!table) {
        alert('No table data to export');
        return;
    }

    let csvContent = 'data:text/csv;charset=utf-8,';
    csvContent += 'Source Datatype,Replicate Datatype,Target Datatype\n';

    const rows = table.querySelectorAll('tr');
    rows.forEach((row, index) => {
        if (index === 0) return; // Skip the header row
        const cols = row.querySelectorAll('td');
        const rowData = Array.from(cols).map(col => `"${col.innerText}"`).join(',');
        csvContent += rowData + '\r\n';
    });

    // Create a link and trigger download
    const encodedUri = encodeURI(csvContent);
    const fileName = `datatype_mapping_${source.replace(/\s+/g, '_')}_to_${target.replace(/\s+/g, '_')}.csv`;
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
