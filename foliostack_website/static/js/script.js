document.addEventListener('DOMContentLoaded', function () {

    // Animate features on scroll
    document.addEventListener("scroll", function() {
        document.querySelectorAll('.tm-work-item-inner').forEach((el) => {
            let position = el.getBoundingClientRect().top;
            if (position < window.innerHeight - 50) {
                el.classList.add('show');
            }
        });
    });

    function showSection(targetId) {
        const targetSection = document.getElementById(targetId);
        if (!targetSection) return;

        // Hide only form sections
        if (targetId === 'section-3') {
            document.getElementById('section-5').style.display = 'none';
        } else if (targetId === 'section-5') {
            document.getElementById('section-3').style.display = 'none';
        }

        // Show the target (login/register) section
        targetSection.style.setProperty('display', 'block', 'important');
        targetSection.scrollIntoView({ behavior: 'smooth' });
    }

    // --- HERO BUTTONS ---
    document.getElementById('show-login-btn')?.addEventListener('click', function(e) {
        e.preventDefault();
        showSection('section-3');
    });

    document.getElementById('show-register-btn')?.addEventListener('click', function(e) {
        e.preventDefault();
        showSection('section-5');
    });

    // --- NAVBAR LINKS ---
    document.querySelectorAll('.single-page-nav a[href^="#section-"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href').substring(1);

            // Handle only login/register with JS
            if (targetId === 'section-3' || targetId === 'section-5') {
                e.preventDefault();
                showSection(targetId);
            } else {
                // Scroll normally for visible sections
                const targetSection = document.getElementById(targetId);
                if (targetSection) {
                    e.preventDefault();
                    targetSection.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    });

    // --- FORM VALIDATION ---
    (function () {
        'use strict';
        const forms = document.querySelectorAll('form');
        forms.forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    })();

    // --- PASSWORD TOGGLE ---
    function setupPasswordToggle(toggleId, passwordId) {
        const toggle = document.getElementById(toggleId);
        const password = document.getElementById(passwordId);

        if (toggle && password) {
            toggle.addEventListener('click', function () {
                // toggle the type attribute
                const type = password.getAttribute('type') === 'password' ? 'text' : 'password';
                password.setAttribute('type', type);
                
                // toggle the eye / eye-slash icon
                this.classList.toggle('fa-eye');
                this.classList.toggle('fa-eye-slash');
            });
        }
    }

    // Setup for login form
    setupPasswordToggle('toggleLoginPassword', 'login_password');

    // Setup for registration form
    setupPasswordToggle('toggleRegisterPassword', 'register_password');
    setupPasswordToggle('toggleRegisterConfirmPassword', 'register_confirm_password');

});
