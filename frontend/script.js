document.addEventListener('DOMContentLoaded', () => {
    // Global variables
    let map;
    let startMarker = null;
    let endMarker = null;
    let startCoords = null;
    let endCoords = null;
    let isSelectingStart = true;

    // DOM elements
    const searchBtn = document.getElementById('search-btn');
    const departureTimeInput = document.getElementById('departure-time');
    const departureLimitInput = document.getElementById('departure-limit');
    const statusMessageDiv = document.getElementById('status-message');
    const jsonOutputTextarea = document.getElementById('json-output');
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('results-container');
    const startCoordsDisplay = document.getElementById('start-coords');
    const endCoordsDisplay = document.getElementById('end-coords');
    const debugToggle = document.getElementById('debug-toggle');
    const debugContent = document.getElementById('debug-content');
    const debugArrow = document.getElementById('debug-arrow');

    // Initialize the application
    initializeApp();

    function initializeApp() {
        initializeMap();
        initializeEventListeners();
        setDefaultDepartureTime();
    }

    function initializeMap() {
        // Initialize map centered on Wrocław
        map = L.map('map').setView([51.1079, 17.0385], 13);

        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Add click event to map
        map.on('click', handleMapClick);

        // Add map instructions
        const instructions = L.control({ position: 'topright' });
        instructions.onAdd = function() {
            const div = L.DomUtil.create('div', 'leaflet-control-custom');
            div.innerHTML = `
                <div class="bg-white p-3 rounded shadow-lg text-sm max-w-xs">
                    <strong>Instructions:</strong><br>
                    1st click: Set start point (🟢)<br>
                    2nd click: Set destination (🔴)<br>
                    Click markers to switch selection
                </div>
            `;
            div.style.backgroundColor = 'transparent';
            div.style.border = 'none';
            return div;
        };
        instructions.addTo(map);
    }

    function initializeEventListeners() {
        searchBtn.addEventListener('click', handleSearch);
        debugToggle.addEventListener('click', toggleDebugSection);
        
        // Validate inputs on change
        departureLimitInput.addEventListener('input', validateInputs);
    }

    function setDefaultDepartureTime() {
        // Set default departure time to current time (rounded to next 5 minutes)
        const now = new Date();
        now.setMinutes(Math.ceil(now.getMinutes() / 5) * 5, 0, 0);
        departureTimeInput.value = now.toISOString().slice(0, 16);
    }

    function handleMapClick(e) {
        const { lat, lng } = e.latlng;

        if (isSelectingStart || !startCoords) {
            setStartPoint(lat, lng);
            isSelectingStart = false;
        } else if (!endCoords) {
            setEndPoint(lat, lng);
        } else {
            // Both points are set, determine which one to replace based on proximity
            const startDistance = map.distance([lat, lng], [startCoords.lat, startCoords.lng]);
            const endDistance = map.distance([lat, lng], [endCoords.lat, endCoords.lng]);
            
            if (startDistance < endDistance) {
                setStartPoint(lat, lng);
            } else {
                setEndPoint(lat, lng);
            }
        }

        validateInputs();
    }

    function setStartPoint(lat, lng) {
        startCoords = { lat, lng };
        
        if (startMarker) {
            map.removeLayer(startMarker);
        }
        
        startMarker = L.marker([lat, lng], {
            icon: createCustomIcon('🟢', 'green')
        }).addTo(map);
        
        startMarker.on('click', () => {
            isSelectingStart = true;
            displayStatus('Click on the map to set a new start point', 'text-blue-600');
        });
        
        startCoordsDisplay.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    }

    function setEndPoint(lat, lng) {
        endCoords = { lat, lng };
        
        if (endMarker) {
            map.removeLayer(endMarker);
        }
        
        endMarker = L.marker([lat, lng], {
            icon: createCustomIcon('🔴', 'red')
        }).addTo(map);
        
        endMarker.on('click', () => {
            isSelectingStart = false;
            displayStatus('Click on the map to set a new destination point', 'text-blue-600');
        });
        
        endCoordsDisplay.textContent = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    }

    function createCustomIcon(emoji, color) {
        return L.divIcon({
            html: `<div style="background-color: white; border: 2px solid ${color}; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 16px; cursor: pointer;">${emoji}</div>`,
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        });
    }

    function validateInputs() {
        const hasValidCoords = startCoords && endCoords;
        const hasValidLimit = departureLimitInput.value >= 1 && departureLimitInput.value <= 20;
        
        searchBtn.disabled = !hasValidCoords || !hasValidLimit;
        
        if (!hasValidCoords) {
            displayStatus('Please select both start and destination points on the map', 'text-yellow-600');
        } else if (!hasValidLimit) {
            displayStatus('Please enter a valid number of departures (1-20)', 'text-yellow-600');
        } else {
            displayStatus('Ready to search for departures', 'text-green-600');
        }
    }

    async function handleSearch() {
        if (!startCoords || !endCoords) {
            displayStatus('Please select both start and destination points', 'text-red-600');
            return;
        }

        const limit = parseInt(departureLimitInput.value) || 5;
        const departureTime = departureTimeInput.value || new Date().toISOString();

        // Build API URL with query parameters
        const baseUrl = 'http://localhost:5001/public_transport/city/wroclaw/closest_departures/';
        const params = new URLSearchParams({
            start_coordinates: `${startCoords.lat},${startCoords.lng}`,
            end_coordinates: `${endCoords.lat},${endCoords.lng}`,
            start_time: departureTime,
            limit: limit.toString()
        });

        const apiUrl = `${baseUrl}?${params.toString()}`;

        displayStatus('🔍 Searching for departures...', 'text-blue-600');
        searchBtn.disabled = true;
        jsonOutputTextarea.value = '';
        resultsSection.classList.add('hidden');

        try {
            const response = await fetch(apiUrl);

            if (!response.ok) {
                let errorMessage = `HTTP Error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    if (errorData.message) {
                        errorMessage += ` - ${errorData.message}`;
                    } else if (errorData.error) {
                        errorMessage += ` - ${errorData.error}`;
                    }
                } catch (parseError) {
                    // If response is not JSON, use default error message
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            
            // Display raw JSON for debugging
            jsonOutputTextarea.value = JSON.stringify(data, null, 2);
            
            // Display formatted results
            displayResults(data);
            
            displayStatus('✅ Departures found successfully!', 'text-green-600');

        } catch (error) {
            console.error("Failed to call API:", error);
            jsonOutputTextarea.value = `Error: ${error.message}`;
            displayStatus(`❌ Error: ${error.message}`, 'text-red-600');
            resultsSection.classList.add('hidden');
        } finally {
            searchBtn.disabled = false;
            validateInputs(); // Re-enable if inputs are still valid
        }
    }

    function displayResults(data) {
        resultsContainer.innerHTML = '';
        
        if (!data || (!Array.isArray(data) && !data.departures)) {
            resultsContainer.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <p class="text-lg">🤷‍♂️ No departure data received</p>
                    <p class="text-sm mt-2">The API response format might be different than expected</p>
                </div>
            `;
            resultsSection.classList.remove('hidden');
            return;
        }

        // Handle different possible response formats
        let departures = [];
        if (Array.isArray(data)) {
            departures = data;
        } else if (data.departures && Array.isArray(data.departures)) {
            departures = data.departures;
        } else if (data.results && Array.isArray(data.results)) {
            departures = data.results;
        }

        if (departures.length === 0) {
            resultsContainer.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <p class="text-lg">🚌 No departures found</p>
                    <p class="text-sm mt-2">Try adjusting your search criteria or check if the API is working correctly</p>
                </div>
            `;
        } else {
            departures.forEach((departure, index) => {
                const departureCard = createDepartureCard(departure, index + 1);
                resultsContainer.appendChild(departureCard);
            });
        }
        
        resultsSection.classList.remove('hidden');
    }

    function createDepartureCard(departure, index) {
        const card = document.createElement('div');
        card.className = 'bg-gray-50 rounded-lg p-4 mb-4 border border-gray-200 hover:shadow-md transition-shadow';
        
        // Extract data with fallbacks for different possible field names
        const stopName = departure.stop_name || departure.stopName || departure.name || 'Unknown Stop';
        const lineId = departure.route_short_name || departure.line_id || departure.lineId || departure.route_id || 'Unknown Line';
        const headsign = departure.trip_headsign || departure.headsign || departure.destination || departure.direction || 'Unknown Destination';
        const departureTime = departure.departure_time || departure.departureTime || departure.scheduled_time || departure.time || 'Unknown Time';
        const distance = departure.distance || departure.distance_meters || null;

        // Format departure time if it's a timestamp
        let formattedTime = departureTime;
        if (departureTime && !isNaN(Date.parse(departureTime))) {
            const date = new Date(departureTime);
            formattedTime = date.toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
            });
        }

        card.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center mb-2">
                        <span class="bg-blue-600 text-white px-3 py-1 rounded-full text-sm font-bold mr-3">
                            ${lineId}
                        </span>
                        <span class="text-lg font-semibold text-gray-800">
                            ${headsign}
                        </span>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-600">
                        <div class="flex items-center">
                            <span class="mr-2">📍</span>
                            <span><strong>Stop:</strong> ${stopName}</span>
                        </div>
                        <div class="flex items-center">
                            <span class="mr-2">🕐</span>
                            <span><strong>Departure:</strong> ${formattedTime}</span>
                        </div>
                        ${distance ? `
                        <div class="flex items-center">
                            <span class="mr-2">📏</span>
                            <span><strong>Distance:</strong> ${Math.round(distance)}m</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
                <div class="ml-4 text-right">
                    <div class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-semibold">
                        #${index}
                    </div>
                </div>
            </div>
        `;
        
        return card;
    }

    function displayStatus(message, colorClass) {
        statusMessageDiv.textContent = message;
        statusMessageDiv.className = `mt-4 text-center text-sm font-semibold ${colorClass}`;
    }

    function toggleDebugSection() {
        const isHidden = debugContent.classList.contains('hidden');
        
        if (isHidden) {
            debugContent.classList.remove('hidden');
            debugArrow.textContent = '▲';
        } else {
            debugContent.classList.add('hidden');
            debugArrow.textContent = '▼';
        }
    }
});
