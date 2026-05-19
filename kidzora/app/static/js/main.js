/**
 * KidZora E-Commerce Platform - Main JavaScript
 */

// Global variables
let currentUser = null;
let notifications = [];

// Initialize on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize modals
    initializeModals();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize auto-refresh for real-time data
    initializeAutoRefresh();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    console.log('KidZora application initialized');
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize modal behaviors
 */
function initializeModals() {
    // Auto-focus first input in modals
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', function () {
            const firstInput = this.querySelector('input:not([type="hidden"]), textarea');
            if (firstInput) {
                firstInput.focus();
            }
        });
    });
    
    // Clear form data when modal is hidden
    document.querySelectorAll('.modal form').forEach(form => {
        const modal = form.closest('.modal');
        modal.addEventListener('hidden.bs.modal', function () {
            form.reset();
            // Clear any validation errors
            form.querySelectorAll('.is-invalid').forEach(element => {
                element.classList.remove('is-invalid');
            });
            form.querySelectorAll('.invalid-feedback').forEach(element => {
                element.remove();
            });
        });
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Bootstrap form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Custom validation for file uploads
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            validateFileSize(this);
        });
    });
}

/**
 * Validate file size
 */
function validateFileSize(input) {
    const maxSize = 5 * 1024 * 1024; // 5MB
    const files = input.files;
    
    for (let file of files) {
        if (file.size > maxSize) {
            showNotification('File size must be less than 5MB', 'error');
            input.value = '';
            return false;
        }
    }
    return true;
}

/**
 * Initialize auto-refresh for real-time data
 */
function initializeAutoRefresh() {
    // Auto-refresh dashboard data every 30 seconds
    if (window.location.pathname.includes('/dashboard')) {
        setInterval(refreshDashboardData, 30000);
    }
    
    // Auto-refresh chat messages every 15 seconds
    if (window.location.pathname.includes('/chat')) {
        setInterval(refreshChatMessages, 15000);
    }
}

/**
 * Refresh dashboard data
 */
function refreshDashboardData() {
    // In a real implementation, this would fetch data via API
    console.log('Refreshing dashboard data...');
}

/**
 * Refresh chat messages
 */
function refreshChatMessages() {
    // In a real implementation, this would fetch new messages via API
    console.log('Refreshing chat messages...');
}

/**
 * Initialize keyboard shortcuts
 */
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + K for search
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            const searchInput = document.querySelector('input[type="search"], input[placeholder*="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape to close modals
        if (event.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                bootstrap.Modal.getInstance(openModal).hide();
            }
        }
    });
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    // No auto-remove — user must close manually via the × button.
}

/**
 * Confirm action
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'PHP') {
    return new Intl.NumberFormat('en-PH', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Format date
 */
function formatDate(dateString, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-PH', { ...defaultOptions, ...options });
}

/**
 * Format time
 */
function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-PH', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format datetime
 */
function formatDateTime(dateString) {
    return `${formatDate(dateString)} at ${formatTime(dateString)}`;
}

/**
 * Debounce function
 */
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

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Copy to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!', 'success', 2000);
    } catch (err) {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy to clipboard', 'error');
    }
}

/**
 * Download data as file
 */
function downloadFile(data, filename, type = 'text/plain') {
    const blob = new Blob([data], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/**
 * Export table data as CSV
 */
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    if (!table) {
        showNotification('Table not found', 'error');
        return;
    }
    
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = [];
        cols.forEach(col => {
            rowData.push(col.textContent.trim());
        });
        csv.push(rowData.join(','));
    });
    
    downloadFile(csv.join('\n'), filename, 'text/csv');
}

/**
 * Loading state management
 */
function setLoading(element, loading = true) {
    if (loading) {
        element.disabled = true;
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText || element.innerHTML;
    }
}

/**
 * API request helper
 */
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const config = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, config);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        showNotification(error.message || 'Request failed', 'error');
        throw error;
    }
}

/**
 * Initialize DataTables for tables
 */
function initializeDataTables() {
    document.querySelectorAll('.datatable').forEach(table => {
        // In a real implementation, you would initialize DataTables library
        console.log('Initializing DataTable for:', table);
    });
}

/**
 * Handle file upload preview
 */
function handleFileUpload(input, previewContainer) {
    const file = input.files[0];
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewContainer.innerHTML = `
                <img src="${e.target.result}" class="img-thumbnail" style="max-height: 200px;">
                <button type="button" class="btn btn-sm btn-danger mt-2" onclick="clearFileUpload('${input.id}', '${previewContainer.id}')">
                    <i class="fas fa-trash"></i> Remove
                </button>
            `;
        };
        reader.readAsDataURL(file);
    }
}

/**
 * Clear file upload
 */
function clearFileUpload(inputId, previewContainerId) {
    document.getElementById(inputId).value = '';
    document.getElementById(previewContainerId).innerHTML = '';
}

// Export functions for global use
window.KidZora = {
    showNotification,
    confirmAction,
    formatCurrency,
    formatDate,
    formatTime,
    formatDateTime,
    copyToClipboard,
    downloadFile,
    exportTableToCSV,
    setLoading,
    apiRequest,
    handleFileUpload,
    clearFileUpload
};
