/**
 * Dashboard JavaScript functionality for customer metrics and charts
 * Requires: Google Charts library, common.js
 */

// Dashboard configuration - these will be set by the template
let dashboardConfig = {
    appUrl: '',
    customerName: ''
};

// Initialize dashboard
function initDashboard(config) {
    dashboardConfig = config;
    
    // Load Google Charts
    google.charts.load('current', {'packages':['corechart', 'line', 'bar']});
    google.charts.setOnLoadCallback(loadAllCards);
}

function loadAllCards() {
    // Load all dashboard cards
    loadCard('boxes_purchased_cumulative_30d', 'purchasedDevicesHistory', updatePurchasedDevices);
    loadCard('boxes_provisioned_pct_cumulative_30d', 'provHistory', updatePctProvisioned);
    loadCard('calls_breakdown_7d', 'cbt', updateCallsCharts);
    loadCard('ratings_average_7d_window_30d', 'ratingsHistory', updateRatings);
    loadCard('boxes_provisioned_cumulative_30d', 'regDevicesHistory', updateProvisionedDevices);
    loadCard('users_active_7d_window_30d', 'sdauHistory', updateActiveUsers);
    loadCard('dialin_count_7d_window_30d', 'dialinsHistory', updateDialins);
    loadCard('users_registered_cumulative_30d', 'regUsersHistory', updateRegUsers);
    loadCard('calls_count_7d_window_30d', 'cpwHistory', updateCallsWeek);
    loadCard('support_tickets_7d_window_30d', 'supportHistory', updateSupport);
    loadCard('comments_recent_7d', 'comments', updateComments);
}

function loadCard(cardType, chartDivId, updateCallback) {
    fetch(dashboardConfig.appUrl + '?card=' + cardType)
        .then(response => response.json())
        .then(data => {
            console.log('Card data for ' + cardType + ':', data);
            if (data.error) {
                console.error('Error loading ' + cardType + ':', data.error);
                document.getElementById(chartDivId).innerHTML = '<div class="alert alert-warning">Error loading data</div>';
            } else {
                updateCallback(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById(chartDivId).innerHTML = '<div class="alert alert-danger">Failed to load data</div>';
        });
}

function refresh(cardType, chartDivId, updateCallback) {
    // Show loading state
    document.getElementById(chartDivId).innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    loadCard(cardType, chartDivId, updateCallback);
}

function refreshWithAnimation(buttonElement, cardType, chartDivId, updateCallback) {
    // Add loading animation
    buttonElement.classList.add('loading');
    buttonElement.disabled = true;
    
    // Show loading in chart area
    document.getElementById(chartDivId).innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
    
    // Load card data
    fetch(dashboardConfig.appUrl + '?card=' + cardType)
        .then(response => response.json())
        .then(data => {
            console.log('Card data for ' + cardType + ':', data);
            if (data.error) {
                console.error('Error loading ' + cardType + ':', data.error);
                document.getElementById(chartDivId).innerHTML = '<div class="alert alert-warning">Error loading data</div>';
            } else {
                updateCallback(data);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById(chartDivId).innerHTML = '<div class="alert alert-danger">Failed to load data</div>';
        })
        .finally(() => {
            // Remove loading animation from button
            setTimeout(() => {
                buttonElement.classList.remove('loading');
                buttonElement.disabled = false;
            }, 500);
        });
}

// Card update functions
function updatePurchasedDevices(data) {
    document.getElementById('purchasedDevices').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'purchasedDevicesHistory', 'Purchased Devices Over Time');
    } else {
        document.getElementById('purchasedDevicesHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updatePctProvisioned(data) {
    document.getElementById('prov').innerText = (data.value || '--') + (data.value !== '--' ? '%' : '');
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'provHistory', '% Devices Provisioned Over Time');
    } else {
        document.getElementById('provHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateCallsCharts(data) {
    if (data.cbt && data.cbt.length > 1) {
        drawPieChart(data.cbt, 'cbt', 'Calls by Type');
    }
    if (data.cbu && data.cbu.length > 1) {
        drawPieChart(data.cbu, 'cbu', 'Calls by # of Users');
    }
    if (data.cbo && data.cbo.length > 1) {
        drawPieChart(data.cbo, 'cbo', 'Calls by OS');
    }
}

function updateProvisionedDevices(data) {
    document.getElementById('regDevices').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'regDevicesHistory', 'Provisioned Devices Over Time');
    } else {
        document.getElementById('regDevicesHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateRegUsers(data) {
    document.getElementById('regUsers').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'regUsersHistory', 'Registered Users Over Time');
    } else {
        document.getElementById('regUsersHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateActiveUsers(data) {
    document.getElementById('sdau').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'sdauHistory', '7-Day Active Users Over Time');
    } else {
        document.getElementById('sdauHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateRatings(data) {
    if (data.value && data.value.avg !== '--') {
        document.getElementById('ratings').innerText = data.value.avg + ' (' + data.value.num + ' ratings)';
    } else {
        document.getElementById('ratings').innerText = '--';
    }
    
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'ratingsHistory', 'Average Ratings Over Time');
    } else {
        document.getElementById('ratingsHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateDialins(data) {
    document.getElementById('dialins').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'dialinsHistory', 'Dialin Sessions Over Time');
    } else {
        document.getElementById('dialinsHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateCallsWeek(data) {
    document.getElementById('cpw').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'cpwHistory', 'Calls Per Week Over Time');
    } else {
        document.getElementById('cpwHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateSupport(data) {
    document.getElementById('support').innerText = data.value || '--';
    if (data.history && data.history.length > 1) {
        drawLineChart(data.history, 'supportHistory', 'Support Tickets Over Time');
    } else {
        document.getElementById('supportHistory').innerHTML = '<div class="text-muted text-center">No data available</div>';
    }
}

function updateComments(data) {
    const commentsDiv = document.getElementById('comments');
    if (data && data.length > 0) {
        let html = '';
        data.forEach((comment, index) => {
            const text = comment[0];
            const fullUser = comment[1];
            const timestamp = comment[2] ? new Date(comment[2]) : null;
            
            // Extract username from email
            const user = fullUser.includes('@') ? fullUser.split('@')[0] : fullUser;
            
            // Get user initial
            const userInitial = user ? user.charAt(0).toUpperCase() : '?';
            
            // Format timestamp
            let timeStr = '';
            if (timestamp) {
                const now = new Date();
                const diffMs = now - timestamp;
                const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                const diffDays = Math.floor(diffHours / 24);
                
                if (diffDays > 0) {
                    timeStr = `${diffDays}d ago`;
                } else if (diffHours > 0) {
                    timeStr = `${diffHours}h ago`;
                } else {
                    timeStr = 'Just now';
                }
            }
            
            html += `
                <div class="comment-item ${index < 3 ? 'recent' : ''}">
                    <div class="comment-avatar">${userInitial}</div>
                    <div class="comment-content">
                        <div class="comment-header">
                            <span class="comment-user">${user}</span>
                            <span class="comment-time">${timeStr}</span>
                        </div>
                        <div class="comment-text">${text}</div>
                    </div>
                </div>
            `;
        });
        commentsDiv.innerHTML = html;
    } else {
        commentsDiv.innerHTML = '<div class="text-muted text-center">No recent comments</div>';
    }
}

// Chart drawing functions
function drawLineChart(data, elementId, title) {
    const chartData = google.visualization.arrayToDataTable(data);
    const options = {
        title: title,
        curveType: 'none',
        legend: { position: 'none' },
        hAxis: {
            showTextEvery: 7
        },
        vAxis: { minValue: 0 }
    };
    
    const chart = new google.visualization.LineChart(document.getElementById(elementId));
    chart.draw(chartData, options);
}

function drawPieChart(data, elementId, title) {
    const chartData = google.visualization.arrayToDataTable(data);
    const options = {
        title: title,
        pieHole: 0.4,
        legend: { position: 'bottom' }
    };
    
    const chart = new google.visualization.PieChart(document.getElementById(elementId));
    chart.draw(chartData, options);
}

// Test events functionality
function testEvents() {
    // Generate test events
    const currentTime = new Date().toISOString();
    
    // Create purchase event
    const purchaseEvent = {
        timestamp: currentTime,
        type: "purchased", 
        company: dashboardConfig.customerName,
        purchased: Math.floor(Math.random() * 10) + 1, // Random 1-10
        provisioned: null,
        serial_number: null,
        box_name: null
    };
    
    // Create provision event
    const provisionEvent = {
        timestamp: currentTime,
        type: "provisioned",
        company: dashboardConfig.customerName,
        purchased: null,
        provisioned: 1,
        serial_number: `SN${Math.floor(Math.random() * 10000)}`,
        box_name: `Box${Math.floor(Math.random() * 1000)}`
    };
    
    // Send events to API
    const events = [purchaseEvent, provisionEvent];
    
    fetch('/api/events', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(events)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Test events sent:', data);
        Utils.showAlert('testEventsStatus', 'success', 'Success', 
            `Generated ${events.length} test events for ${dashboardConfig.customerName}`);
        
        // Refresh relevant cards after a short delay
        setTimeout(() => {
            refresh('boxes_purchased_cumulative_30d', 'purchasedDevicesHistory', updatePurchasedDevices);
            refresh('boxes_provisioned_cumulative_30d', 'regDevicesHistory', updateProvisionedDevices);
        }, 2000);
    })
    .catch(error => {
        console.error('Error:', error);
        Utils.handleApiError(error, 'testEventsStatus');
    });
}

// Make functions available globally
window.Dashboard = {
    init: initDashboard,
    refresh: refresh,
    refreshWithAnimation: refreshWithAnimation,
    testEvents: testEvents
};
