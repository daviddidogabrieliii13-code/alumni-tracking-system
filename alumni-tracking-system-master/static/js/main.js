(function () {
    function onReady(callback) {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", callback);
            return;
        }
        callback();
    }

    function initTheme() {
        const root = document.documentElement;
        const toggleButton = document.getElementById("themeToggle");
        const storageKey = "wvsu_theme";

        function readStoredTheme() {
            try {
                return window.localStorage.getItem(storageKey);
            } catch (_error) {
                return null;
            }
        }

        function writeStoredTheme(value) {
            try {
                window.localStorage.setItem(storageKey, value);
            } catch (_error) {
                // Ignore storage errors safely
            }
        }

        function setTheme(theme, persist) {
            const isDark = theme === "dark";
            if (isDark) {
                root.setAttribute("data-theme", "dark");
            } else {
                root.removeAttribute("data-theme");
            }

            if (toggleButton) {
                toggleButton.setAttribute("aria-pressed", isDark ? "true" : "false");
                const icon = toggleButton.querySelector("i");
                const label = toggleButton.querySelector(".theme-toggle-label");
                if (icon) {
                    icon.classList.remove("fa-moon", "fa-sun");
                    icon.classList.add(isDark ? "fa-sun" : "fa-moon");
                }
                if (label) {
                    label.textContent = isDark ? "Light Mode" : "Dark Mode";
                }
            }

            if (persist) {
                writeStoredTheme(isDark ? "dark" : "light");
            }

            window.dispatchEvent(
                new CustomEvent("themechange", {
                    detail: { theme: isDark ? "dark" : "light" },
                })
            );
        }

        const storedTheme = readStoredTheme();
        const prefersDark = Boolean(
            window.matchMedia &&
            window.matchMedia("(prefers-color-scheme: dark)").matches
        );
        const initialTheme = storedTheme === "dark" || storedTheme === "light"
            ? storedTheme
            : prefersDark
                ? "dark"
                : "light";

        setTheme(initialTheme, false);

        if (toggleButton) {
            toggleButton.addEventListener("click", function () {
                const isDark = root.getAttribute("data-theme") === "dark";
                setTheme(isDark ? "light" : "dark", true);
            });
        }
    }

    function initNavbar() {
        const navToggle = document.getElementById("navToggle");
        const navMenu = document.getElementById("navMenu");
        const navOverlay = document.getElementById("navOverlay");
        const navbar = document.getElementById("navbar");

        if (!navMenu) {
            return;
        }

        function setNavOpen(isOpen) {
            navMenu.classList.toggle("active", isOpen);
            document.body.classList.toggle("nav-open", isOpen);
            if (navToggle) {
                navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
            }
            if (navOverlay) {
                navOverlay.classList.toggle("active", isOpen);
            }
        }

        if (navToggle) {
            navToggle.addEventListener("click", function () {
                setNavOpen(!navMenu.classList.contains("active"));
            });
        }

        if (navOverlay) {
            navOverlay.addEventListener("click", function () {
                setNavOpen(false);
            });
        }

        document.querySelectorAll(".dropdown-toggle").forEach(function (toggle) {
            toggle.addEventListener("click", function (event) {
                const dropdown = toggle.closest(".dropdown");
                if (!dropdown) {
                    return;
                }
                const href = toggle.getAttribute("href");
                if (!href || href === "#") {
                    event.preventDefault();
                }
                if (window.matchMedia("(max-width: 820px)").matches) {
                    dropdown.classList.toggle("open");
                }
            });
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                setNavOpen(false);
            }
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 820) {
                setNavOpen(false);
            }
        });

        window.addEventListener("scroll", function () {
            if (!navbar) {
                return;
            }
            navbar.classList.toggle("scrolled", window.scrollY > 20);
        });
    }

    function initFlashDismiss() {
        document.querySelectorAll(".alert").forEach(function (alert) {
            const closeButton = alert.querySelector(".alert-close");
            const removeAlert = function () {
                alert.style.opacity = "0";
                alert.style.transform = "translateX(8px)";
                window.setTimeout(function () {
                    alert.remove();
                }, 220);
            };

            window.setTimeout(removeAlert, 5500);
            if (closeButton) {
                closeButton.addEventListener("click", removeAlert);
            }
        });
    }

    function initSurveyProgress() {
        const surveyForm = document.getElementById("surveyForm");
        const progressFill = document.querySelector(".survey-progress-fill");
        if (!surveyForm || !progressFill) {
            return;
        }

        const fields = Array.from(
            surveyForm.querySelectorAll("input, select, textarea")
        ).filter(function (field) {
            return field.type !== "hidden";
        });

        function isFilled(field) {
            if (field.type === "radio") {
                const selected = surveyForm.querySelector(
                    'input[name="' + field.name + '"]:checked'
                );
                return Boolean(selected);
            }
            return Boolean(field.value && field.value.trim() !== "");
        }

        function updateProgress() {
            if (!fields.length) {
                progressFill.style.width = "0%";
                return;
            }
            const uniqueNames = new Map();
            fields.forEach(function (field) {
                const key = field.type === "radio" ? field.name : field.name + field.type;
                if (!uniqueNames.has(key)) {
                    uniqueNames.set(key, field);
                }
            });

            let filled = 0;
            uniqueNames.forEach(function (field) {
                if (isFilled(field)) {
                    filled += 1;
                }
            });

            const percentage = Math.round((filled / uniqueNames.size) * 100);
            progressFill.style.width = percentage + "%";
        }

        surveyForm.addEventListener("input", updateProgress);
        surveyForm.addEventListener("change", updateProgress);
        updateProgress();
    }

    function initSearchFilters() {
        const alumniSearch = document.getElementById("alumniSearch");
        if (alumniSearch) {
            const cards = document.querySelectorAll(".alumni-card");
            alumniSearch.addEventListener("input", function () {
                const term = alumniSearch.value.trim().toLowerCase();
                cards.forEach(function (card) {
                    const text = card.textContent.toLowerCase();
                    card.style.display = text.includes(term) ? "" : "none";
                });
            });
        }

        const eventTypeFilter = document.getElementById("eventTypeFilter");
        if (eventTypeFilter) {
            const eventCards = document.querySelectorAll(".event-card");
            eventTypeFilter.addEventListener("change", function () {
                const selected = eventTypeFilter.value;
                eventCards.forEach(function (card) {
                    if (!selected || selected === "all") {
                        card.style.display = "";
                        return;
                    }
                    const typeElement = card.querySelector(".event-type");
                    const typeValue = typeElement ? typeElement.textContent.toLowerCase() : "";
                    card.style.display = typeValue.includes(selected) ? "" : "none";
                });
            });
        }
    }

    function initSmoothAnchors() {
        document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
            anchor.addEventListener("click", function (event) {
                const targetId = anchor.getAttribute("href");
                if (!targetId || targetId === "#") {
                    return;
                }
                const target = document.querySelector(targetId);
                if (!target) {
                    return;
                }
                event.preventDefault();
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });
    }

    function initOtpCountdown() {
        const countdown = document.getElementById("otpCountdown");
        if (!countdown) {
            return;
        }
        let seconds = parseInt(countdown.dataset.seconds, 10);
        if (Number.isNaN(seconds) || seconds < 0) {
            seconds = 0;
        }

        function tick() {
            countdown.textContent = String(seconds);
            if (seconds <= 0) {
                return;
            }
            seconds -= 1;
            window.setTimeout(tick, 1000);
        }

        tick();
    }

    function initOtpInput() {
        const otpInput = document.querySelector(".otp-input");
        if (!otpInput) {
            return;
        }

        function sanitizeOtp(value) {
            return value.replace(/\D/g, "").slice(0, 6);
        }

        otpInput.value = sanitizeOtp(otpInput.value || "");

        otpInput.addEventListener("input", function () {
            otpInput.value = sanitizeOtp(otpInput.value || "");
        });

        otpInput.addEventListener("paste", function (event) {
            const pastedText = (event.clipboardData || window.clipboardData).getData("text");
            const sanitized = sanitizeOtp(pastedText || "");
            if (!sanitized) {
                return;
            }
            event.preventDefault();
            otpInput.value = sanitized;
        });
    }

    function initCharts() {
        if (typeof Chart === "undefined") {
            return;
        }
        function applyChartTheme() {
            const styles = window.getComputedStyle(document.documentElement);
            const chartColor = (styles.getPropertyValue("--text-secondary") || "").trim();
            Chart.defaults.font.family = "Poppins, Lato, Roboto, sans-serif";
            Chart.defaults.color = chartColor || "#3e5674";

            const instances = Chart.instances;
            if (!instances) {
                return;
            }

            if (typeof instances.forEach === "function") {
                instances.forEach(function (chart) {
                    if (chart && typeof chart.update === "function") {
                        chart.update("none");
                    }
                });
                return;
            }

            Object.values(instances).forEach(function (chart) {
                if (chart && typeof chart.update === "function") {
                    chart.update("none");
                }
            });
        }

        applyChartTheme();
        window.addEventListener("themechange", applyChartTheme);
    }

    function initDegreeOtherFields() {
        const degreeSelects = document.querySelectorAll(".js-degree-select");
        if (!degreeSelects.length) {
            return;
        }

        degreeSelects.forEach(function (selectField) {
            const otherInputId = selectField.dataset.otherInputId;
            if (!otherInputId) {
                return;
            }

            const otherField = document.getElementById(otherInputId);
            if (!otherField) {
                return;
            }

            const form = selectField.closest("form");

            function toggleOtherField() {
                const isOther = selectField.value === "__other__";
                otherField.hidden = !isOther;
                otherField.required = isOther;
                if (!isOther) {
                    otherField.value = "";
                    otherField.setCustomValidity("");
                }
            }

            function applyOtherValueBeforeSubmit() {
                if (selectField.value !== "__other__") {
                    const existingCustom = selectField.querySelector(
                        'option[data-custom-generated="true"]'
                    );
                    if (existingCustom) {
                        existingCustom.remove();
                    }
                    return true;
                }

                const customCourse = otherField.value.trim();
                if (!customCourse) {
                    otherField.setCustomValidity("Please enter your full course name.");
                    otherField.reportValidity();
                    return false;
                }

                otherField.setCustomValidity("");
                let customOption = selectField.querySelector(
                    'option[data-custom-generated="true"]'
                );
                if (!customOption) {
                    customOption = document.createElement("option");
                    customOption.dataset.customGenerated = "true";
                    selectField.appendChild(customOption);
                }
                customOption.value = customCourse;
                customOption.textContent = customCourse;
                selectField.value = customCourse;
                return true;
            }

            selectField.addEventListener("change", toggleOtherField);
            otherField.addEventListener("input", function () {
                otherField.setCustomValidity("");
            });

            if (form) {
                form.addEventListener("submit", function (event) {
                    if (!applyOtherValueBeforeSubmit()) {
                        event.preventDefault();
                    }
                });
            }

            toggleOtherField();
        });
    }

    function initAlumniModuleStepper() {
        const form = document.getElementById("alumniModuleForm");
        if (!form) {
            return;
        }

        const stepButtons = Array.from(document.querySelectorAll(".module-step-btn"));
        const stepPanels = Array.from(document.querySelectorAll(".module-step-panel"));
        const prevButton = document.getElementById("modulePrevStep");
        const nextButton = document.getElementById("moduleNextStep");
        if (!stepButtons.length || !stepPanels.length) {
            return;
        }

        let currentStepIndex = 0;
        form.classList.add("js-stepper");

        function showStep(nextIndex) {
            const safeIndex = Math.max(0, Math.min(nextIndex, stepPanels.length - 1));
            currentStepIndex = safeIndex;

            stepButtons.forEach(function (button, index) {
                button.classList.toggle("active", index === safeIndex);
            });
            stepPanels.forEach(function (panel, index) {
                panel.classList.toggle("active", index === safeIndex);
            });

            if (prevButton) {
                prevButton.disabled = safeIndex === 0;
            }
            if (nextButton) {
                const lastStep = safeIndex === stepPanels.length - 1;
                nextButton.disabled = lastStep;
                nextButton.style.display = lastStep ? "none" : "inline-flex";
            }
        }

        stepButtons.forEach(function (button, index) {
            button.addEventListener("click", function () {
                showStep(index);
            });
        });

        if (prevButton) {
            prevButton.addEventListener("click", function () {
                showStep(currentStepIndex - 1);
            });
        }

        if (nextButton) {
            nextButton.addEventListener("click", function () {
                showStep(currentStepIndex + 1);
            });
        }

        showStep(0);
    }

    function initProfilePhotoPreview() {
        const photoInputs = document.querySelectorAll("[data-photo-preview]");
        if (!photoInputs.length || typeof FileReader === "undefined") {
            return;
        }

        photoInputs.forEach(function (inputField) {
            const previewSelector = inputField.dataset.photoPreview;
            if (!previewSelector) {
                return;
            }
            const preview = document.querySelector(previewSelector);
            if (!preview) {
                return;
            }

            inputField.addEventListener("change", function () {
                const selectedFile = inputField.files && inputField.files[0];
                if (!selectedFile) {
                    return;
                }

                const reader = new FileReader();
                reader.onload = function (event) {
                    if (event && event.target && event.target.result) {
                        preview.src = event.target.result;
                    }
                };
                reader.readAsDataURL(selectedFile);
            });
        });
    }

    onReady(function () {
        initTheme();
        initNavbar();
        initFlashDismiss();
        initSurveyProgress();
        initSearchFilters();
        initSmoothAnchors();
        initOtpCountdown();
        initOtpInput();
        initCharts();
        initDegreeOtherFields();
        initAlumniModuleStepper();
        initProfilePhotoPreview();
    });
})();
