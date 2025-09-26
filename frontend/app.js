// CropGuard AI Multi-Crop Detection System v3.0
const API_BASE_URL = 'http://127.0.0.1:5000';

// Global state
let currentPrediction = null;
let selectedRating = 0;
let predictionHistory = [];
let currentHistoryPage = 1;
let historyLimit = 15;
let totalHistoryPages = 1;
let systemStats = {};

// DOM elements
let uploadArea, fileInput, imagePreview, previewImg, analyzeBtn, removeBtn;
let loadingOverlay, navMenu, navLinks;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    console.log('🚀 Initializing CropGuard AI v3.0...');
    
    // Get DOM elements
    uploadArea = document.getElementById('uploadArea');
    fileInput = document.getElementById('imageFile');
    imagePreview = document.getElementById('imagePreview');
    previewImg = document.getElementById('previewImg');
    analyzeBtn = document.getElementById('analyzeBtn');
    removeBtn = document.getElementById('removeImage');
    loadingOverlay = document.getElementById('loadingOverlay');
    navMenu = document.getElementById('navMenu');
    navLinks = document.querySelectorAll('.nav-link');

    // Setup functionality
    setupNavigation();
    setupFileUpload();
    setupContactForm();
    setupHistoryControls();
    setupResearchTabs();
    loadInitialData();
    
    console.log('✅ App initialized successfully');
}

// ========== NAVIGATION ==========
function setupNavigation() {
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            navigateToPage(page);
        });
    });
}

function navigateToPage(pageId) {
    console.log('🧭 Navigating to:', pageId);
    
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Remove active from nav links
    navLinks.forEach(link => {
        link.classList.remove('active');
    });

    // Show target page
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
        
        // Update nav
        const activeLink = document.querySelector(`[data-page="${pageId}"]`);
        if (activeLink) {
            activeLink.classList.add('active');
        }

        // Load page content
        switch(pageId) {
            case 'analytics':
                loadAnalytics();
                break;
            case 'history':
                loadAndDisplayHistory();
                break;
            case 'research':
                initializeResearchTabs();
                break;
        }
    }
}

// ========== FILE UPLOAD & DETECTION ==========
function setupFileUpload() {
    if (!uploadArea || !fileInput) return;

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeImage);
    }

    if (removeBtn) {
        removeBtn.addEventListener('click', removeImage);
    }
}

function handleFileSelect(file) {
    console.log('📁 File selected:', file.name, `(${(file.size / 1024 / 1024).toFixed(2)} MB)`);

    // Validate file
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
        showAlert('Please select a valid image file (JPG, PNG, GIF)', 'error');
        return;
    }

    if (file.size > 16 * 1024 * 1024) {
        showAlert('File size must be less than 16MB', 'error');
        return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        imagePreview.classList.remove('hidden');
        analyzeBtn.classList.remove('hidden');
        
        // Update image info
        const fileNameSpan = document.getElementById('imageFileName');
        const fileSizeSpan = document.getElementById('imageFileSize');
        if (fileNameSpan) fileNameSpan.textContent = file.name;
        if (fileSizeSpan) fileSizeSpan.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
        
        // Clear previous results
        const resultsContainer = document.getElementById('analysisResults');
        if (resultsContainer) {
            resultsContainer.classList.add('hidden');
        }
    };
    reader.readAsDataURL(file);
}

function removeImage() {
    fileInput.value = '';
    imagePreview.classList.add('hidden');
    analyzeBtn.classList.add('hidden');
    
    const resultsContainer = document.getElementById('analysisResults');
    if (resultsContainer) {
        resultsContainer.classList.add('hidden');
    }
}

async function analyzeImage() {
    if (!fileInput.files[0]) {
        showAlert('Please select an image first!', 'error');
        return;
    }

    // Get selected model type
    const selectedModel = document.querySelector('input[name="detectionType"]:checked');
    if (!selectedModel) {
        showAlert('Please select a detection type (Fruit or Leaf)', 'error');
        return;
    }

    const modelType = selectedModel.value;
    const loadingText = document.getElementById('loadingText');
    const loadingSubtext = document.getElementById('loadingSubtext');

    // Update loading messages based on model type
    if (modelType === 'fruit') {
        loadingText.textContent = 'Analyzing Fruit...';
        loadingSubtext.textContent = '🍎 Using ResNet50V2 architecture for precise fruit disease detection';
    } else {
        loadingText.textContent = 'Analyzing Leaf...';
        loadingSubtext.textContent = '🍃 Using CNN architecture for comprehensive leaf disease analysis';
    }

    showLoading(true);
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';

    try {
        const formData = new FormData();
        formData.append('image', fileInput.files[0]);
        formData.append('model_type', modelType);

        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            console.log('🎯 Prediction received:', data);
            displayResults(data);
            currentPrediction = data;
            addToHistory(data);
        } else {
            showAlert(data.error || 'Analysis failed. Please try again.', 'error');
        }

    } catch (error) {
        console.error('❌ Network error:', error);
        showAlert('Network error. Please check your connection and try again.', 'error');
    } finally {
        showLoading(false);
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-microscope"></i> Analyze Crop Health';
    }
}

function displayResults(data) {
    const resultsContainer = document.getElementById('analysisResults');
    if (!resultsContainer) return;

    const confidence = (data.confidence * 100).toFixed(1);
    const diseaseInfo = data.disease_info || {};
    const diseaseName = formatDiseaseName(data.predicted_class);
    const modelType = data.model_type;
    const modelIcon = modelType === 'fruit' ? '🍎' : '🍃';

    // Get confidence color and status
    const confidenceColor = getConfidenceColor(confidence);
    const confidenceStatus = getConfidenceStatus(confidence);

    resultsContainer.innerHTML = `
        <div class="enhanced-results">
            <div class="result-header">
                <div class="result-title-section">
                    <div class="model-indicator">
                        <span class="model-icon">${modelIcon}</span>
                        <span class="model-name">${modelType === 'fruit' ? 'Fruit' : 'Leaf'} Detection</span>
                    </div>
                    <h3 class="disease-name">${diseaseName}</h3>
                </div>
                <div class="confidence-section">
                    <div class="confidence-badge ${confidenceColor}">${confidence}%</div>
                    <span class="confidence-status">${confidenceStatus}</span>
                </div>
            </div>

            <div class="confidence-bar-container">
                <div class="confidence-bar ${confidenceColor}" style="width: ${confidence}%;"></div>
                <div class="confidence-markers">
                    <span class="marker" style="left: 80%;">80%</span>
                    <span class="marker" style="left: 95%;">95%</span>
                </div>
            </div>

            <div class="disease-details">
                ${diseaseInfo.type ? `
                <div class="detail-section">
                    <h4><span class="icon">🔬</span> Disease Information</h4>
                    <div class="info-grid">
                        <div class="info-item">
                            <strong>Type:</strong> ${diseaseInfo.type}
                        </div>
                        ${diseaseInfo.pathogen ? `
                        <div class="info-item">
                            <strong>Pathogen:</strong> <em>${diseaseInfo.pathogen}</em>
                        </div>
                        ` : ''}
                        ${diseaseInfo.severity ? `
                        <div class="info-item">
                            <strong>Severity:</strong> 
                            <span class="severity-badge severity-${(diseaseInfo.severity || 'medium').toLowerCase()}">
                                ${diseaseInfo.severity}
                            </span>
                        </div>
                        ` : ''}
                        ${diseaseInfo.economic_impact ? `
                        <div class="info-item">
                            <strong>Economic Impact:</strong> ${diseaseInfo.economic_impact}
                        </div>
                        ` : ''}
                    </div>
                    ${diseaseInfo.description ? `<p class="description">${diseaseInfo.description}</p>` : ''}
                </div>
                ` : ''}

                ${diseaseInfo.symptoms && diseaseInfo.symptoms.length > 0 ? `
                <div class="detail-section">
                    <h4><span class="icon">⚠️</span> Key Symptoms</h4>
                    <ul class="symptoms-list">
                        ${diseaseInfo.symptoms.map(symptom => `<li><i class="fas fa-exclamation-triangle"></i> ${symptom}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}

                ${diseaseInfo.remedies && diseaseInfo.remedies.length > 0 ? `
                <div class="detail-section treatment-section">
                    <h4><span class="icon">💊</span> Treatment & Chemical Remedies</h4>
                    <ul class="remedies-list">
                        ${diseaseInfo.remedies.map(remedy => `<li><i class="fas fa-prescription-bottle-alt"></i> ${remedy}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}

                ${diseaseInfo.organic_remedies && diseaseInfo.organic_remedies.length > 0 ? `
                <div class="detail-section organic-section">
                    <h4><span class="icon">🌱</span> Organic & Biological Remedies</h4>
                    <ul class="remedies-list organic">
                        ${diseaseInfo.organic_remedies.map(remedy => `<li><i class="fas fa-leaf"></i> ${remedy}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}

                ${diseaseInfo.prevention && diseaseInfo.prevention.length > 0 ? `
                <div class="detail-section prevention-section">
                    <h4><span class="icon">🛡️</span> Prevention Strategies</h4>
                    <ul class="prevention-list">
                        ${diseaseInfo.prevention.map(prevention => `<li><i class="fas fa-shield-alt"></i> ${prevention}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}

                ${diseaseInfo.maintenance && diseaseInfo.maintenance.length > 0 ? `
                <div class="detail-section maintenance-section">
                    <h4><span class="icon">🌿</span> Ongoing Maintenance</h4>
                    <ul class="maintenance-list">
                        ${diseaseInfo.maintenance.map(maintenance => `<li><i class="fas fa-tools"></i> ${maintenance}</li>`).join('')}
                    </ul>
                </div>
                ` : ''}
            </div>

            <div class="feedback-section">
                <h4><i class="fas fa-star"></i> Rate this prediction</h4>
                <div class="rating-stars">
                    ${[1,2,3,4,5].map(i => `<span class="star" data-rating="${i}">⭐</span>`).join('')}
                </div>
                <div class="feedback-controls">
                    <label class="checkbox-label">
                        <input type="checkbox" id="correctPrediction">
                        <span class="checkmark"></span>
                        This prediction is accurate
                    </label>
                    <textarea id="feedbackComment" 
                              placeholder="Additional comments (optional)" 
                              rows="3" maxlength="500"></textarea>
                    <div class="feedback-actions">
                        <button class="btn btn--primary" onclick="submitFeedback()">
                            <i class="fas fa-paper-plane"></i> Submit Feedback
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    resultsContainer.classList.remove('hidden');
    setupRatingStars();
}

// Helper functions for display
function formatDiseaseName(className) {
    return className.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getConfidenceColor(confidence) {
    if (confidence >= 95) return 'high';
    if (confidence >= 80) return 'medium';
    return 'low';
}

function getConfidenceStatus(confidence) {
    if (confidence >= 95) return 'Excellent';
    if (confidence >= 80) return 'Good';
    return 'Fair';
}

// ========== RATING SYSTEM ==========
function setupRatingStars() {
    const stars = document.querySelectorAll('.star');
    stars.forEach((star, index) => {
        star.addEventListener('click', () => {
            selectedRating = index + 1;
            updateStarDisplay();
        });
        
        star.addEventListener('mouseover', () => {
            updateStarDisplay(index + 1);
        });
    });
    
    const starsContainer = document.querySelector('.rating-stars');
    if (starsContainer) {
        starsContainer.addEventListener('mouseleave', () => {
            updateStarDisplay(selectedRating);
        });
    }
}

function updateStarDisplay(rating = selectedRating) {
    const stars = document.querySelectorAll('.star');
    stars.forEach((star, index) => {
        star.classList.toggle('active', index < rating);
    });
}

async function submitFeedback() {
    if (!currentPrediction || !currentPrediction.prediction_id) {
        showAlert('No prediction to rate', 'error');
        return;
    }
    
    if (selectedRating === 0) {
        showAlert('Please select a rating', 'error');
        return;
    }
    
    const isCorrect = document.getElementById('correctPrediction').checked;
    const comment = document.getElementById('feedbackComment').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prediction_id: currentPrediction.prediction_id,
                rating: selectedRating,
                is_correct: isCorrect,
                comment: comment
            })
        });
        
        if (response.ok) {
            showAlert('Thank you for your feedback! This helps improve our AI models.', 'success');
            document.querySelector('.feedback-controls').innerHTML = `
                <div class="success-message">
                    <i class="fas fa-check-circle"></i> 
                    Feedback submitted successfully! Thank you for helping us improve.
                </div>
            `;
        } else {
            const data = await response.json();
            showAlert(data.error || 'Failed to submit feedback', 'error');
        }
    } catch (error) {
        showAlert('Network error: ' + error.message, 'error');
    }
}

// ========== ANALYTICS ==========
async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE_URL}/analytics`);
        const data = await response.json();
        
        if (response.ok) {
            displayAnalytics(data);
        } else {
            console.error('Failed to load analytics:', data.error);
            showAlert('Failed to load analytics data', 'error');
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
        showAlert('Network error loading analytics', 'error');
    }
}

function displayAnalytics(data) {
    // Update overview cards
    updateElement('totalPredictionsCount', data.total_predictions || 0);
    updateElement('totalUsersCount', data.total_users || 0);
    updateElement('totalContacts', data.total_contacts || 0);
    updateElement('averageAccuracy', `${((data.user_reported_accuracy || 0)).toFixed(1)}%`);

    // Update model distribution
    displayModelDistribution(data.model_distribution || []);
    
    // Update disease distribution
    displayDiseaseDistribution(data.disease_distribution || []);
    
    // Update daily activity
    displayDailyActivity(data.daily_predictions || []);
    
    // Update user feedback
    updateElement('averageRating', (data.average_rating || 4.8).toFixed(1));
    updateElement('userAccuracy', `${(data.user_reported_accuracy || 94.2).toFixed(1)}%`);
}

function displayModelDistribution(distribution) {
    const container = document.getElementById('modelDistributionChart');
    if (!container || distribution.length === 0) {
        if (container) container.innerHTML = '<div class="no-data">No distribution data available</div>';
        return;
    }

    const total = distribution.reduce((sum, item) => sum + item.count, 0);
    const html = distribution.map(item => {
        const percentage = total > 0 ? ((item.count / total) * 100).toFixed(1) : 0;
        const modelIcon = item.model === 'fruit' ? '🍎' : '🍃';
        const modelName = item.model === 'fruit' ? 'Fruit Detection' : 'Leaf Detection';
        
        return `
            <div class="chart-item">
                <div class="chart-header">
                    <span class="chart-icon">${modelIcon}</span>
                    <span class="chart-label">${modelName}</span>
                    <span class="chart-percentage">${percentage}%</span>
                </div>
                <div class="chart-bar-wrapper">
                    <div class="chart-bar ${item.model}" style="width: ${percentage}%"></div>
                </div>
                <div class="chart-count">${item.count} predictions</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function displayDiseaseDistribution(distribution) {
    const container = document.getElementById('diseaseDistributionChart');
    if (!container || distribution.length === 0) {
        if (container) container.innerHTML = '<div class="no-data">No disease data available</div>';
        return;
    }

    const maxCount = Math.max(...distribution.map(item => item.count));
    const html = distribution.slice(0, 8).map(item => {
        const percentage = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
        const modelIcon = item.model === 'fruit' ? '🍎' : '🍃';
        
        return `
            <div class="disease-chart-item">
                <div class="disease-info">
                    <span class="disease-icon">${modelIcon}</span>
                    <span class="disease-name">${formatDiseaseName(item.disease)}</span>
                </div>
                <div class="disease-bar-wrapper">
                    <div class="disease-bar ${item.model}" style="width: ${percentage}%"></div>
                </div>
                <div class="disease-count">${item.count}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function displayDailyActivity(activity) {
    const container = document.getElementById('dailyActivityChart');
    if (!container || activity.length === 0) {
        if (container) container.innerHTML = '<div class="no-data">No activity data available</div>';
        return;
    }

    const maxCount = Math.max(...activity.map(item => item.count));
    const html = activity.slice(-7).map(item => {
        const percentage = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
        const date = new Date(item.date).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
        const modelIcon = item.model === 'fruit' ? '🍎' : '🍃';
        
        return `
            <div class="activity-chart-item">
                <div class="activity-date">${date}</div>
                <div class="activity-bar-wrapper">
                    <div class="activity-bar ${item.model}" style="height: ${percentage}%" 
                         title="${item.count} predictions"></div>
                </div>
                <div class="activity-count">${item.count}</div>
                <div class="activity-model">${modelIcon}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = `<div class="activity-chart">${html}</div>`;
}

// ========== HISTORY MANAGEMENT ==========
function setupHistoryControls() {
    // Search functionality
    const searchInput = document.getElementById('historySearch');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(filterHistory, 300));
    }

    // Clear search
    const clearSearchBtn = document.getElementById('clearSearch');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            filterHistory();
        });
    }

    // Filter controls
    const filters = ['modelFilter', 'diseaseFilter', 'confidenceFilter'];
    filters.forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', filterHistory);
        }
    });

    // Action buttons
    const refreshBtn = document.getElementById('refreshHistory');
    const exportBtn = document.getElementById('exportHistory');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            currentHistoryPage = 1;
            loadAndDisplayHistory();
        });
    }

    if (exportBtn) {
        exportBtn.addEventListener('click', exportHistory);
    }

    // Pagination
    const paginationButtons = ['firstPage', 'prevPage', 'nextPage', 'lastPage'];
    paginationButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', () => handlePagination(btnId));
        }
    });
}

async function loadAndDisplayHistory() {
    try {
        showHistoryLoading(true);
        
        const offset = (currentHistoryPage - 1) * historyLimit;
        const modelFilter = document.getElementById('modelFilter')?.value || '';
        
        let url = `${API_BASE_URL}/history?limit=${historyLimit}&offset=${offset}`;
        if (modelFilter) {
            url += `&model_type=${modelFilter}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (response.ok) {
            predictionHistory = data;
            displayHistory();
            updateHistoryStats();
        } else {
            showAlert('Failed to load history', 'error');
        }
    } catch (error) {
        console.error('Error loading history:', error);
        showAlert('Network error loading history', 'error');
    } finally {
        showHistoryLoading(false);
    }
}

function displayHistory() {
    const historyContainer = document.getElementById('historyResults');
    if (!historyContainer) return;

    if (predictionHistory.length === 0) {
        historyContainer.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">📝</div>
                <h3>No predictions yet</h3>
                <p>Start analyzing some crops to see your history here!</p>
                <button class="btn btn--primary" onclick="navigateToPage('detect')">
                    <i class="fas fa-camera"></i> Start Detection
                </button>
            </div>
        `;
        return;
    }

    const historyHTML = predictionHistory.map(item => {
        const confidence = (item.confidence * 100).toFixed(1);
        const confidenceColor = getConfidenceColor(confidence);
        const modelIcon = item.model_type === 'fruit' ? '🍎' : '🍃';
        const date = new Date(item.timestamp);
        
        return `
            <div class="history-item">
                <div class="history-header">
                    <div class="history-disease-info">
                        <span class="history-model-icon">${modelIcon}</span>
                        <h4 class="history-disease-name">${formatDiseaseName(item.predicted_class)}</h4>
                        <span class="history-model-type">${item.model_type} detection</span>
                    </div>
                    <div class="history-meta">
                        <div class="confidence-badge ${confidenceColor}">${confidence}%</div>
                        <div class="history-timestamp">
                            <i class="fas fa-clock"></i>
                            ${date.toLocaleDateString()} ${date.toLocaleTimeString()}
                        </div>
                    </div>
                </div>
                
                <div class="history-details">
                    ${item.rating ? `
                        <div class="history-rating">
                            <span class="rating-label">Rating:</span>
                            <div class="star-display">
                                ${'★'.repeat(item.rating)}${'☆'.repeat(5 - item.rating)}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${item.is_correct !== null ? `
                        <div class="history-accuracy">
                            <span class="accuracy-label">User Feedback:</span>
                            <span class="accuracy-value ${item.is_correct ? 'correct' : 'incorrect'}">
                                <i class="fas fa-${item.is_correct ? 'check' : 'times'}"></i>
                                ${item.is_correct ? 'Correct' : 'Incorrect'}
                            </span>
                        </div>
                    ` : ''}
                </div>
                
                ${item.comment ? `
                    <div class="history-comment">
                        <i class="fas fa-comment"></i>
                        <span class="comment-text">"${item.comment}"</span>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    historyContainer.innerHTML = historyHTML;
    updatePaginationInfo();
}

function updateHistoryStats() {
    if (predictionHistory.length === 0) return;

    // Total count
    updateElement('historyTotalCount', predictionHistory.length);

    // Average confidence
    const avgConfidence = predictionHistory.reduce((sum, item) => sum + item.confidence, 0) / predictionHistory.length;
    updateElement('historyAvgConfidence', `${(avgConfidence * 100).toFixed(1)}%`);

    // Most common disease
    const diseaseCount = {};
    predictionHistory.forEach(item => {
        diseaseCount[item.predicted_class] = (diseaseCount[item.predicted_class] || 0) + 1;
    });
    
    const mostCommon = Object.entries(diseaseCount).reduce((a, b) => 
        diseaseCount[a[0]] > diseaseCount[b[0]] ? a : b
    );
    
    updateElement('historyTopDisease', formatDiseaseName(mostCommon[0]));
}

function handlePagination(action) {
    const totalPages = Math.ceil(predictionHistory.length / historyLimit) || 1;
    
    switch(action) {
        case 'firstPage':
            currentHistoryPage = 1;
            break;
        case 'prevPage':
            if (currentHistoryPage > 1) currentHistoryPage--;
            break;
        case 'nextPage':
            if (currentHistoryPage < totalPages) currentHistoryPage++;
            break;
        case 'lastPage':
            currentHistoryPage = totalPages;
            break;
    }
    
    loadAndDisplayHistory();
}

function updatePaginationInfo() {
    const totalPages = Math.ceil(predictionHistory.length / historyLimit) || 1;
    updateElement('pageInfo', `Page ${currentHistoryPage} of ${totalPages}`);
    
    // Update button states
    const firstBtn = document.getElementById('firstPage');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    const lastBtn = document.getElementById('lastPage');
    
    if (firstBtn) firstBtn.disabled = currentHistoryPage === 1;
    if (prevBtn) prevBtn.disabled = currentHistoryPage === 1;
    if (nextBtn) nextBtn.disabled = currentHistoryPage === totalPages;
    if (lastBtn) lastBtn.disabled = currentHistoryPage === totalPages;
}

function filterHistory() {
    // This would filter the displayed history based on search and filters
    console.log('🔍 Filtering history...');
    // Implementation would filter predictionHistory array and re-display
}

function exportHistory() {
    if (predictionHistory.length === 0) {
        showAlert('No history to export', 'error');
        return;
    }

    const csvContent = "data:text/csv;charset=utf-8," + 
        "Date,Time,Model Type,Disease,Confidence,Rating,Correct,Comment\n" +
        predictionHistory.map(item => {
            const date = new Date(item.timestamp);
            return [
                date.toLocaleDateString(),
                date.toLocaleTimeString(),
                item.model_type,
                `"${item.predicted_class}"`,
                (item.confidence * 100).toFixed(1) + '%',
                item.rating || '',
                item.is_correct !== null ? (item.is_correct ? 'Yes' : 'No') : '',
                `"${(item.comment || '').replace(/"/g, '""')}"`
            ].join(',');
        }).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `cropguard_history_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showAlert('History exported successfully!', 'success');
}

function showHistoryLoading(show) {
    const historyContainer = document.getElementById('historyResults');
    if (!historyContainer) return;
    
    if (show) {
        historyContainer.innerHTML = `
            <div class="loading-history">
                <div class="spinner-small"></div>
                <p>Loading prediction history...</p>
            </div>
        `;
    }
}

// ========== RESEARCH TABS ==========
function setupResearchTabs() {
    const tabs = document.querySelectorAll('.research-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            switchResearchTab(targetTab);
        });
    });
}

function switchResearchTab(tabName) {
    // Remove active class from all tabs and contents
    document.querySelectorAll('.research-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.research-tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Add active class to selected tab and content
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

function initializeResearchTabs() {
    // Initialize with models tab active
    switchResearchTab('models');
}

// ========== CONTACT FORM ==========
function setupContactForm() {
    const contactForm = document.getElementById('contactForm');
    const messageTextarea = document.getElementById('contactMessage');
    const charCounter = document.getElementById('messageCharCount');
    
    if (messageTextarea && charCounter) {
        messageTextarea.addEventListener('input', function() {
            const currentLength = this.value.length;
            charCounter.textContent = currentLength;
            
            if (currentLength > 950) {
                charCounter.style.color = '#dc2626';
            } else if (currentLength > 800) {
                charCounter.style.color = '#f59e0b';
            } else {
                charCounter.style.color = '#6b7280';
            }
        });
    }

    if (contactForm) {
        contactForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                name: formData.get('name').trim(),
                email: formData.get('email').trim(),
                subject: formData.get('subject'),
                message: formData.get('message').trim()
            };
            
            // Validation
            if (!data.name || !data.email || !data.message) {
                showAlert('Please fill in all required fields', 'error');
                return;
            }
            
            if (data.message.length > 1000) {
                showAlert('Message is too long (max 1000 characters)', 'error');
                return;
            }
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
            
            try {
                const response = await fetch(`${API_BASE_URL}/contact`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showAlert('Message sent successfully! We\'ll get back to you soon.', 'success');
                    this.reset();
                    charCounter.textContent = '0';
                    
                    // Show WhatsApp option
                    if (result.whatsapp_notification) {
                        setTimeout(() => {
                            if (confirm('Would you like to send a WhatsApp message as well for faster response?')) {
                                window.open(result.whatsapp_notification, '_blank');
                            }
                        }, 2000);
                    }
                } else {
                    showAlert(result.error || 'Failed to send message. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Contact form error:', error);
                showAlert('Network error. Please check your connection and try again.', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    }
}

// ========== UTILITY FUNCTIONS ==========
function addToHistory(prediction) {
    predictionHistory.unshift(prediction);
    if (predictionHistory.length > 100) {
        predictionHistory = predictionHistory.slice(0, 100);
    }
}

async function loadInitialData() {
    try {
        // Load system stats
        const statsResponse = await fetch(`${API_BASE_URL}/stats`);
        if (statsResponse.ok) {
            systemStats = await statsResponse.json();
            updateNavStats();
        }
        
        // Load initial history
        await loadAndDisplayHistory();
        
    } catch (error) {
        console.error('Error loading initial data:', error);
    }
}

function updateNavStats() {
    updateElement('navTotalPredictions', systemStats.total_predictions || 0);
    updateElement('navTotalUsers', systemStats.total_users || 0);
}

function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function showLoading(show) {
    if (loadingOverlay) {
        loadingOverlay.classList.toggle('hidden', !show);
    }
}

function showAlert(message, type = 'error') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    
    const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
    alertDiv.innerHTML = `
        <div class="alert-content">
            <span class="alert-icon">${icon}</span>
            <span class="alert-message">${message}</span>
            <button class="alert-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        z-index: 10000;
        min-width: 300px;
        max-width: 500px;
        background: ${type === 'error' ? '#dc2626' : type === 'success' ? '#10b981' : '#3b82f6'};
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        animation: slideInRight 0.3s ease;
        border-left: 4px solid rgba(255,255,255,0.3);
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => alertDiv.remove(), 300);
        }
    }, 5000);
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .spinner-small {
        width: 20px;
        height: 20px;
        border: 2px solid #f3f3f3;
        border-top: 2px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        display: inline-block;
        margin-right: 10px;
    }
`;
document.head.appendChild(style);

console.log('🎉 CropGuard AI v3.0 loaded successfully!');