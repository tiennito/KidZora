/**
 * KidZora – Auth / Email Verification
 * Reads session data from #kz-ev-cfg data attributes to avoid Jinja in JS files.
 */
document.addEventListener('DOMContentLoaded', function() {
    const emailForm     = document.getElementById('emailVerificationForm');
    const codeForm      = document.getElementById('codeVerificationForm');
    const sendCodeBtn   = document.getElementById('sendCodeBtn');
    const resendCodeBtn = document.getElementById('resendCodeBtn');
    const countdown     = document.getElementById('countdown');

    let countdownTimer;

    // Handle email form submission
    emailForm.addEventListener('submit', function(e) {
        const email = document.getElementById('email').value;
        if (!email) {
            e.preventDefault();
            alert('Please enter your email address');
            return false;
        }
        sendCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending Code...';
        sendCodeBtn.disabled  = true;
    });

    // Handle code form submission
    codeForm.addEventListener('submit', function(e) {
        const code = document.getElementById('confirmation_code').value;
        if (!code || code.length !== 6) {
            e.preventDefault();
            alert('Please enter a valid 6-digit confirmation code');
            return false;
        }
    });

    // Handle resend code
    resendCodeBtn.addEventListener('click', function() {
        const email = document.getElementById('email').value;
        if (!email) {
            alert('Please enter your email address first');
            return;
        }

        resendCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Sending...';
        resendCodeBtn.disabled  = true;

        fetch('/auth/resend_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                startCountdown(60);
                alert('Confirmation code resent to your email');
            } else {
                alert('Failed to resend code. Please try again.');
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('Failed to resend code. Please try again.');
        })
        .finally(function() {
            resendCodeBtn.innerHTML = '<i class="fas fa-redo me-1"></i>Resend Code';
            resendCodeBtn.disabled  = false;
        });
    });

    // Countdown timer
    function startCountdown(seconds) {
        let remaining = seconds;
        if (countdownTimer) clearInterval(countdownTimer);
        resendCodeBtn.disabled = true;
        countdownTimer = setInterval(function() {
            if (remaining > 0) {
                countdown.textContent = 'Resend available in ' + remaining + 's';
                remaining--;
            } else {
                clearInterval(countdownTimer);
                countdown.textContent  = '';
                resendCodeBtn.disabled = false;
            }
        }, 1000);
    }

    // Pre-fill email from server session (injected via data attribute)
    const cfg       = document.getElementById('kz-ev-cfg');
    const verEmail  = cfg && cfg.dataset.verificationEmail ? cfg.dataset.verificationEmail : null;
    if (verEmail) {
        emailForm.style.display = 'none';
        codeForm.style.display  = 'block';
        document.getElementById('email').value = verEmail;
        startCountdown(60);
    }
});
