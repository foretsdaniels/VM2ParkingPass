// Drag and Drop File Upload
document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('file');
    const uploadForm = document.getElementById('uploadForm');

    if (dropZone && fileInput) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        // Handle dropped files
        dropZone.addEventListener('drop', handleDrop, false);

        // Handle click on drop zone
        dropZone.addEventListener('click', () => fileInput.click());
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone.classList.add('border-primary', 'bg-primary', 'bg-opacity-10');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-primary', 'bg-primary', 'bg-opacity-10');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            fileInput.files = files;
            updateFileDisplay(files[0]);
        }
    }

    function updateFileDisplay(file) {
        const allowedTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
        
        if (allowedTypes.includes(file.type) || file.name.match(/\.(csv|xls|xlsx)$/i)) {
            dropZone.innerHTML = `
                <i class="fas fa-file-check fa-3x text-success mb-3"></i>
                <p class="mb-2"><strong>${file.name}</strong></p>
                <p class="text-muted small">File ready for upload (${formatFileSize(file.size)})</p>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="clearFile()">
                    <i class="fas fa-times"></i> Clear
                </button>
            `;
        } else {
            dropZone.innerHTML = `
                <i class="fas fa-file-times fa-3x text-danger mb-3"></i>
                <p class="mb-2 text-danger"><strong>Invalid file type</strong></p>
                <p class="text-muted small">Please select a CSV, XLS, or XLSX file</p>
            `;
        }
    }

    // File input change handler
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                updateFileDisplay(e.target.files[0]);
            }
        });
    }

    // Form submission handler
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const submitBtn = uploadForm.querySelector('button[type="submit"]');
            const originalContent = submitBtn.innerHTML;
            
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            submitBtn.disabled = true;
            
            // Re-enable button after 30 seconds as fallback
            setTimeout(() => {
                submitBtn.innerHTML = originalContent;
                submitBtn.disabled = false;
            }, 30000);
        });
    }
});

function clearFile() {
    const fileInput = document.getElementById('file');
    const dropZone = document.getElementById('dropZone');
    
    fileInput.value = '';
    dropZone.innerHTML = `
        <i class="fas fa-cloud-upload-alt fa-3x text-muted mb-3"></i>
        <p class="mb-2">Drag and drop your Visual Matrix export file here</p>
        <p class="text-muted small">or click the button above to browse</p>
    `;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Column mapping helpers
function validateColumnMapping() {
    const confirmation = document.getElementById('confirmation_col')?.value;
    const arrival = document.getElementById('arrival_col')?.value;
    const departure = document.getElementById('departure_col')?.value;
    
    // Only run validation if we're on the column mapping page
    const submitBtn = document.querySelector('form button[type="submit"]');
    if (document.getElementById('confirmation_col') && document.getElementById('arrival_col') && document.getElementById('departure_col') && submitBtn) {
        if (confirmation && arrival && departure) {
            submitBtn.disabled = false;
            submitBtn.classList.remove('btn-secondary');
            submitBtn.classList.add('btn-primary');
        } else {
            submitBtn.disabled = true;
            submitBtn.classList.remove('btn-primary');
            submitBtn.classList.add('btn-secondary');
        }
    }
}

// Initialize column mapping validation
document.addEventListener('DOMContentLoaded', function() {
    const columnSelects = document.querySelectorAll('#confirmation_col, #arrival_col, #departure_col');
    
    // Only add validation if we're on the column mapping page
    if (columnSelects.length > 0) {
        columnSelects.forEach(select => {
            select.addEventListener('change', validateColumnMapping);
        });
        
        // Initial validation
        validateColumnMapping();
    }
});

// Utility functions for data tables
function sortTable(columnIndex) {
    const table = document.querySelector('table tbody');
    if (!table) return;
    
    const rows = Array.from(table.rows);
    const isNumeric = !isNaN(rows[0]?.cells[columnIndex]?.textContent);
    
    rows.sort((a, b) => {
        const aVal = a.cells[columnIndex].textContent.trim();
        const bVal = b.cells[columnIndex].textContent.trim();
        
        if (isNumeric) {
            return parseFloat(aVal) - parseFloat(bVal);
        } else {
            return aVal.localeCompare(bVal);
        }
    });
    
    rows.forEach(row => table.appendChild(row));
}

// Error handling and user feedback
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}
