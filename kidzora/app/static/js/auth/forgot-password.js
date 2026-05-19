/**
 * KidZora – Auth / Forgot Password (3-step flow)
 * Reads API URLs from #kz-fp-cfg data attributes to avoid Jinja in JS files.
 */
(function() {
    const _el = document.getElementById('kz-fp-cfg');
    window._FP = {
        sendUrl:   _el ? _el.dataset.sendUrl   : '',
        verifyUrl: _el ? _el.dataset.verifyUrl  : '',
        resetUrl:  _el ? _el.dataset.resetUrl   : ''
    };
})();

// ── helpers ───────────────────────────────────────────────────────────────────
function showAlert(msg, type) {
    type = type || 'danger';
    const el = document.createElement('div');
    el.className = 'alert alert-' + type + ' alert-dismissible fade show mt-3';
    el.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    document.querySelector('.card-body').prepend(el);
    setTimeout(function() { el.remove(); }, 5000);
}

function setLoading(btn, loading, defaultHtml) {
    btn.disabled = loading;
    btn.innerHTML = loading
        ? '<i class="fas fa-spinner fa-spin me-2"></i>Please wait...'
        : defaultHtml;
}

function goBack(step) { showStep(step); }

function showStep(n) {
    ['step1', 'step2', 'step3', 'stepSuccess'].forEach(function(id, i) {
        document.getElementById(id).style.display =
            (i + 1 === n || (n === 4 && id === 'stepSuccess')) ? 'block' : 'none';
    });
    const pct = n <= 3 ? ((n - 1) / 2) * 100 : 100;
    document.getElementById('stepProgress').style.width = pct + '%';
    ['circle1', 'circle2', 'circle3'].forEach(function(id, i) {
        const c = document.getElementById(id);
        c.className  = 'rounded-circle text-white d-flex align-items-center justify-content-center mx-auto step-circle';
        c.style.cssText = 'width:36px;height:36px;font-weight:bold;';
        if (i + 1 < n) {
            c.classList.add('bg-success');
            c.innerHTML = '<i class="fas fa-check"></i>';
        } else if (i + 1 === n) {
            c.classList.add('bg-primary');
            c.innerHTML = i + 1;
        } else {
            c.classList.add('bg-secondary');
            c.innerHTML = i + 1;
        }
    });
}

function togglePwd(id, btn) {
    const inp    = document.getElementById(id);
    const isText = inp.type === 'text';
    inp.type     = isText ? 'password' : 'text';
    btn.innerHTML = '<i class="fas fa-eye' + (isText ? '' : '-slash') + '"></i>';
}

// ── Step 1: Send code ─────────────────────────────────────────────────────────
async function sendCode() {
    const email = document.getElementById('email').value.trim();
    if (!email) { showAlert('Please enter your email address.'); return; }

    const btn = document.getElementById('sendCodeBtn');
    setLoading(btn, true);

    try {
        const r = await fetch(_FP.sendUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const d = await r.json();
        if (d.success) {
            document.getElementById('emailDisplay').textContent = email;
            showStep(2);
            startCountdown(60);
        } else {
            showAlert(d.message);
        }
    } catch(e) {
        showAlert('Network error. Please try again.');
    } finally {
        setLoading(btn, false, '<i class="fas fa-paper-plane me-2"></i>Send Verification Code');
    }
}

// ── Step 2: Verify OTP ────────────────────────────────────────────────────────
async function verifyCode() {
    const code = document.getElementById('otpCode').value.trim();
    if (code.length !== 6) { showAlert('Please enter the 6-digit code.'); return; }

    try {
        const r = await fetch(_FP.verifyUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const d = await r.json();
        if (d.success) {
            showStep(3);
        } else {
            showAlert(d.message);
        }
    } catch(e) {
        showAlert('Network error. Please try again.');
    }
}

async function resendCode() {
    const email = document.getElementById('email').value.trim();
    const btn   = document.getElementById('resendBtn');
    setLoading(btn, true);

    try {
        const r = await fetch(_FP.sendUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const d = await r.json();
        if (d.success) {
            showAlert('Code resent! Check your inbox.', 'success');
            startCountdown(60);
        } else {
            showAlert(d.message);
        }
    } catch(e) {
        showAlert('Network error.');
    } finally {
        setLoading(btn, false, '<i class="fas fa-redo me-1"></i>Resend Code');
    }
}

let countdownTimer;
function startCountdown(seconds) {
    clearInterval(countdownTimer);
    const btn = document.getElementById('resendBtn');
    const el  = document.getElementById('countdown');
    btn.disabled = true;
    let s = seconds;
    el.textContent = 'Resend in ' + s + 's';
    countdownTimer = setInterval(function() {
        s--;
        el.textContent = s > 0 ? 'Resend in ' + s + 's' : '';
        if (s <= 0) {
            clearInterval(countdownTimer);
            btn.disabled = false;
        }
    }, 1000);
}

// ── Step 3: Reset password ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('newPassword').addEventListener('input', function() {
        const val = this.value;
        let strength = 0;
        if (val.length >= 8)          strength++;
        if (/[A-Z]/.test(val))        strength++;
        if (/[a-z]/.test(val))        strength++;
        if (/[0-9]/.test(val))        strength++;
        if (/[^A-Za-z0-9]/.test(val)) strength++;

        const bar   = document.getElementById('strengthBar');
        const label = document.getElementById('strengthLabel');
        const pct   = (strength / 5) * 100;
        bar.style.width = pct + '%';
        const levels = ['', 'Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];
        const colors = ['', 'danger', 'warning', 'info', 'primary', 'success'];
        bar.className     = 'progress-bar bg-' + (colors[strength] || 'secondary');
        label.textContent = levels[strength] || '';
        label.className   = 'text-' + (colors[strength] || 'muted') + ' small';
    });

    document.getElementById('otpCode').addEventListener('input', function() {
        this.value = this.value.replace(/\D/g, '');
        if (this.value.length === 6) verifyCode();
    });
});

async function resetPassword() {
    const pw  = document.getElementById('newPassword').value;
    const cpw = document.getElementById('confirmPassword').value;

    if (!pw)        { showAlert('Please enter a new password.');  return; }
    if (pw !== cpw) { showAlert('Passwords do not match.');        return; }

    const pattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()\-_=+\[\]{};:'",.<>?/\\|`~]).{8,}$/;
    if (!pattern.test(pw)) {
        showAlert('Password must be at least 8 characters with uppercase, lowercase, number and special character.');
        return;
    }

    try {
        const r = await fetch(_FP.resetUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw, confirm_password: cpw })
        });
        const d = await r.json();
        if (d.success) {
            document.getElementById('step3').style.display        = 'none';
            document.getElementById('stepSuccess').style.display  = 'block';
            document.getElementById('stepProgress').style.width   = '100%';
        } else {
            showAlert(d.message);
        }
    } catch(e) {
        showAlert('Network error. Please try again.');
    }
}
