/**
 * Setup page JavaScript functionality for BigQuery and Firestore setup
 * Requires: common.js
 */

// Initialize setup page functionality
function initSetup() {
    // Setup BigQuery button handler
    const bigQueryButton = document.getElementById('setupBigQuery');
    if (bigQueryButton) {
        bigQueryButton.addEventListener('click', handleBigQuerySetup);
    }

    // Setup Firestore button handler
    const firestoreButton = document.getElementById('setupFirestore');
    if (firestoreButton) {
        firestoreButton.addEventListener('click', handleFirestoreSetup);
    }

    // Create demo data button handler
    const demoDataButton = document.getElementById('createDemoData');
    if (demoDataButton) {
        demoDataButton.addEventListener('click', handleCreateDemoData);
    }

    // Check demo data status button handler
    const checkStatusButton = document.getElementById('checkDemoDataStatus');
    if (checkStatusButton) {
        checkStatusButton.addEventListener('click', handleCheckDemoDataStatus);
    }
}

function handleBigQuerySetup() {
    const button = this;
    const statusDiv = document.getElementById('setupStatus');
    
    // Check if service is unavailable
    if (button.disabled && button.textContent.includes('Service Unavailable')) {
        Utils.showAlert('setupStatus', 'danger', 'Cannot Set Up BigQuery', 
            'BigQuery service is not available. Please check your configuration and restart the application.');
        return;
    }
    
    // Show loading state
    Utils.setButtonLoading(button, true, 'Setting up BigQuery...');
    statusDiv.innerHTML = '';
    
    // Make API call
    fetch('/api/setup_bigquery', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success" role="alert">
                    <h4 class="alert-heading">Success!</h4>
                    <p>${data.message}</p>
                    <hr>
                    <p class="mb-0">Project ID: <strong>${data.project_id}</strong><br>
                    Dataset ID: <strong>${data.dataset_id}</strong></p>
                </div>
            `;
            button.innerHTML = 'Setup Complete ✓';
            button.className = 'btn btn-success';
        } else {
            Utils.showAlert('setupStatus', 'danger', 'Error', data.message);
            Utils.setButtonLoading(button, false);
        }
    })
    .catch(error => {
        Utils.handleApiError(error, 'setupStatus');
        Utils.setButtonLoading(button, false);
    });
}

function handleFirestoreSetup() {
    const button = this;
    const statusDiv = document.getElementById('firestoreSetupStatus');
    
    // Check if service is unavailable
    if (button.disabled && button.textContent.includes('Service Unavailable')) {
        Utils.showAlert('firestoreSetupStatus', 'danger', 'Cannot Set Up Firestore',
            'Firestore service is not available. Please check your configuration and restart the application.');
        return;
    }
    
    // Show loading state
    Utils.setButtonLoading(button, true, 'Setting up Firestore...');
    statusDiv.innerHTML = '';
    
    // Make API call
    fetch('/api/setup_firestore', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusDiv.innerHTML = `
                <div class="alert alert-success" role="alert">
                    <h4 class="alert-heading">Success!</h4>
                    <p>${data.message}</p>
                    <hr>
                    <p class="mb-0">Project ID: <strong>${data.project_id}</strong><br>
                    Database ID: <strong>${data.database_id}</strong></p>
                </div>
            `;
            button.innerHTML = 'Setup Complete ✓';
            button.className = 'btn btn-success';
        } else {
            Utils.showAlert('firestoreSetupStatus', 'danger', 'Error', data.message);
            Utils.setButtonLoading(button, false);
        }
    })
    .catch(error => {
        Utils.handleApiError(error, 'firestoreSetupStatus');
        Utils.setButtonLoading(button, false);
    });
}

function handleCreateDemoData() {
    const button = this;
    const statusDiv = document.getElementById('demoDataStatus');
    
    // Show loading state
    Utils.setButtonLoading(button, true, 'Creating Demo Data...');
    statusDiv.innerHTML = '';
    
    // Get user limit value
    const userLimitInput = document.getElementById('userLimit');
    const userLimit = userLimitInput ? userLimitInput.value : '';
    
    // Make API call
    fetch('/api/create_demo_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_limit: userLimit })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let statsHtml = '';
            if (data.stats) {
                statsHtml = '<h6>Generated Data:</h6><ul>';
                for (const [key, value] of Object.entries(data.stats)) {
                    const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    statsHtml += `<li><strong>${displayKey}</strong>: ${Utils.formatNumber(value)}</li>`;
                }
                statsHtml += '</ul>';
            }
            
            statusDiv.innerHTML = `
                <div class="alert alert-success" role="alert">
                    <h4 class="alert-heading">Success!</h4>
                    <p>${data.message}</p>
                    <hr>
                    ${statsHtml}
                </div>
            `;
            button.innerHTML = 'Demo Data Created ✓';
            button.className = 'btn btn-success';
        } else {
            Utils.showAlert('demoDataStatus', 'danger', 'Error', data.message);
            Utils.setButtonLoading(button, false);
        }
    })
    .catch(error => {
        Utils.handleApiError(error, 'demoDataStatus');
        Utils.setButtonLoading(button, false);
    });
}

function handleCheckDemoDataStatus() {
    const button = this;
    const statusDiv = document.getElementById('setupStatus');
    
    // Show loading state
    Utils.setButtonLoading(button, true, 'Checking Status...');
    
    // Make API call
    fetch('/api/demo_data_status')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            let collectionsHtml = '';
            if (data.collections) {
                collectionsHtml = '<h6>Collection Status:</h6><ul>';
                for (const [collection, stats] of Object.entries(data.collections)) {
                    if (stats.error) {
                        collectionsHtml += `<li><strong>${collection}</strong>: Error - ${stats.error}</li>`;
                    } else {
                        const realDocs = stats.real_documents || 0;
                        const totalDocs = stats.total_documents || 0;
                        const placeholder = stats.has_placeholder ? ' (has placeholder)' : '';
                        collectionsHtml += `<li><strong>${collection}</strong>: ${Utils.formatNumber(realDocs)} documents${placeholder}</li>`;
                    }
                }
                collectionsHtml += '</ul>';
            }
            
            statusDiv.innerHTML = `
                <div class="alert alert-info" role="alert">
                    <h4 class="alert-heading">Demo Data Status</h4>
                    <p>${data.message}</p>
                    <hr>
                    ${collectionsHtml}
                </div>
            `;
        } else {
            Utils.showAlert('setupStatus', 'danger', 'Error', data.message);
        }
        
        Utils.setButtonLoading(button, false);
    })
    .catch(error => {
        Utils.handleApiError(error, 'setupStatus');
        Utils.setButtonLoading(button, false);
    });
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initSetup);

// Make Setup functions available globally
window.Setup = {
    init: initSetup
};
