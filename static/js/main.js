/* ==================== WVSU ALUMNI SYSTEM JAVASCRIPT ==================== */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Navigation Toggle
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Navbar Scroll Effect
    const navbar = document.getElementById('navbar');
    if (navbar) {
        window.addEventListener('scroll', function() {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        });
    }

    // Flash Messages Auto-dismiss
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100px)';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });

    // Alert Close Button
    const alertCloseButtons = document.querySelectorAll('.alert-close');
    alertCloseButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const alert = this.parentElement;
            alert.style.opacity = '0';
            alert.style.transform = 'translateX(100px)';
            setTimeout(function() {
                alert.remove();
            }, 300);
        });
    });

    // Survey Progress
    const surveyForm = document.getElementById('surveyForm');
    if (surveyForm) {
        const inputs = surveyForm.querySelectorAll('input, select, textarea');
        const progressBar = document.querySelector('.survey-progress-fill');
        
        function updateProgress() {
            let filled = 0;
            const total = inputs.length;
            
            inputs.forEach(function(input) {
                if (input.value && input.value.trim() !== '') {
                    filled++;
                }
            });
            
            const percentage = (filled / total) * 100;
            if (progressBar) {
                progressBar.style.width = percentage + '%';
            }
        }
        
        inputs.forEach(function(input) {
            input.addEventListener('change', updateProgress);
            input.addEventListener('input', updateProgress);
        });
    }

    // Tab Functionality
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const target = this.getAttribute('data-tab');
            
            tabButtons.forEach(function(btn) {
                btn.classList.remove('active');
            });
            tabContents.forEach(function(content) {
                content.classList.remove('active');
            });
            
            this.classList.add('active');
            document.getElementById(target).classList.add('active');
        });
    });

    // Accordion Functionality
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    
    accordionHeaders.forEach(function(header) {
        header.addEventListener('click', function() {
            const item = this.parentElement;
            item.classList.toggle('active');
        });
    });

    // Modal Functionality
    const modalTriggers = document.querySelectorAll('[data-modal]');
    const modals = document.querySelectorAll('.modal');
    
    modalTriggers.forEach(function(trigger) {
        trigger.addEventListener('click', function(e) {
            e.preventDefault();
            const modalId = this.getAttribute('data-modal');
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('active');
            }
        });
    });
    
    modals.forEach(function(modal) {
        const closeBtn = modal.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                modal.classList.remove('active');
            });
        }
        
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });

    // Search Functionality
    const searchInputs = document.querySelectorAll('.search-box input');
    
    searchInputs.forEach(function(input) {
        input.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const target = this.getAttribute('data-search');
            
            if (target) {
                const items = document.querySelectorAll(target);
                items.forEach(function(item) {
                    const text = item.textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
            }
        });
    });

    // Form Validation
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Rating Star Hover Effect
    const ratingLabels = document.querySelectorAll('.rating-label');
    
    ratingLabels.forEach(function(label) {
        label.addEventListener('mouseenter', function() {
            const input = this.previousElementSibling;
            const group = this.parentElement;
            const labels = group.querySelectorAll('.rating-label');
            const index = Array.from(labels).indexOf(this);
            
            labels.forEach(function(l, i) {
                if (i <= index) {
                    l.style.color = '#E9C46A';
                }
            });
        });
        
        label.addEventListener('mouseleave', function() {
            const group = this.parentElement;
            const labels = group.querySelectorAll('.rating-label');
            const checked = group.querySelector('.rating-option:checked');
            
            labels.forEach(function(l) {
                l.style.color = '';
            });
            
            if (checked) {
                const checkedLabel = checked.nextElementSibling;
                const checkedIndex = Array.from(labels).indexOf(checkedLabel);
                
                labels.forEach(function(l, i) {
                    if (i <= checkedIndex) {
                        l.style.color = '#E9C46A';
                    }
                });
            }
        });
    });

    // Job Filter
    const filterForm = document.querySelector('.filter-form');
    if (filterForm) {
        const jobTypeFilter = filterForm.querySelector('[name="job_type"]');
        const locationFilter = filterForm.querySelector('[name="location"]');
        
        function applyFilters() {
            const jobCards = document.querySelectorAll('.job-card');
            
            jobCards.forEach(function(card) {
                let show = true;
                
                if (jobTypeFilter && jobTypeFilter.value) {
                    const jobType = card.querySelector('.job-type').textContent.toLowerCase();
                    if (!jobType.includes(jobTypeFilter.value.toLowerCase())) {
                        show = false;
                    }
                }
                
                if (locationFilter && locationFilter.value) {
                    const location = card.querySelector('.job-meta-item:first-child').textContent.toLowerCase();
                    if (!location.includes(locationFilter.value.toLowerCase())) {
                        show = false;
                    }
                }
                
                card.style.display = show ? '' : 'none';
            });
        }
        
        if (jobTypeFilter) {
            jobTypeFilter.addEventListener('change', applyFilters);
        }
        if (locationFilter) {
            locationFilter.addEventListener('input', applyFilters);
        }
    }

    // Alumni Directory Filter
    const alumniSearch = document.getElementById('alumniSearch');
    const alumniCards = document.querySelectorAll('.alumni-card');
    
    if (alumniSearch) {
        alumniSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            
            alumniCards.forEach(function(card) {
                const name = card.querySelector('.alumni-name').textContent.toLowerCase();
                const degree = card.querySelector('.alumni-degree').textContent.toLowerCase();
                
                if (name.includes(searchTerm) || degree.includes(searchTerm)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Event Type Filter
    const eventTypeFilter = document.getElementById('eventTypeFilter');
    const eventCards = document.querySelectorAll('.event-card');
    
    if (eventTypeFilter) {
        eventTypeFilter.addEventListener('change', function() {
            const filterValue = this.value;
            
            eventCards.forEach(function(card) {
                if (!filterValue || filterValue === 'all') {
                    card.style.display = '';
                } else {
                    const eventType = card.querySelector('.event-type').textContent.toLowerCase().replace(/\s+/g, '-');
                    if (eventType.includes(filterValue)) {
                        card.style.display = '';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        });
    }

    // Profile Photo Preview
    const photoInput = document.getElementById('profilePhotoInput');
    const photoPreview = document.getElementById('photoPreview');
    
    if (photoInput && photoPreview) {
        photoInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    photoPreview.src = e.target.result;
                    photoPreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Smooth Scroll for Anchor Links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Chart Initialization (for Analytics Page)
    const chartCanvases = document.querySelectorAll('.chart-canvas');
    
    if (typeof Chart !== 'undefined' && chartCanvases.length > 0) {
        chartCanvases.forEach(function(canvas) {
            const ctx = canvas.getContext('2d');
            const chartType = canvas.getAttribute('data-chart-type');
            const chartData = JSON.parse(canvas.getAttribute('data-chart-data'));
            
            new Chart(ctx, {
                type: chartType,
                data: chartData.data,
                options: chartData.options
            });
        });
    }

    // Loading Spinner
    window.showLoading = function() {
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(loader);
    };
    
    window.hideLoading = function() {
        const loader = document.querySelector('.loading-overlay');
        if (loader) {
            loader.remove();
        }
    };

    // Copy to Clipboard
    const copyButtons = document.querySelectorAll('[data-copy]');
    
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-copy');
            const target = document.getElementById(targetId);
            
            if (target) {
                navigator.clipboard.writeText(target.value).then(function() {
                    alert('Copied to clipboard!');
                });
            }
        });
    });

    // Tooltip Initialization
    const tooltips = document.querySelectorAll('.tooltip');
    
    tooltips.forEach(function(element) {
        element.addEventListener('mouseenter', function() {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip-text';
            tooltip.textContent = tooltipText;
            this.appendChild(tooltip);
        });
        
        element.addEventListener('mouseleave', function() {
            const tooltip = this.querySelector('.tooltip-text');
            if (tooltip) {
                tooltip.remove();
            }
        });
    });
});

// Utility Functions
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

function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-PH', {
        style: 'currency',
        currency: 'PHP'
    }).format(amount);
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
}
