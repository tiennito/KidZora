/**
 * KidZora – Auth / Register Single (All-in-one registration with confirmation modal)
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing single page registration form...');

    // Toggle role-specific fields based on account type
    function toggleRoleFields() {
        const role         = document.querySelector('input[name="role"]:checked').value;
        const sellerFields = document.getElementById('sellerFields');
        const riderFields  = document.getElementById('riderFields');

        // --- Seller ---
        if (role === 'seller') {
            sellerFields.style.display = 'block';
            const businessName       = document.getElementById('business_name');
            const businessType       = document.getElementById('business_type');
            const sellerIdType       = document.getElementById('seller_id_type');
            const sellerIdNumber     = document.getElementById('seller_id_number');
            const sellerIdFile       = document.getElementById('seller_id_file');
            const businessPermitFile = document.getElementById('business_permit_file');
            const birFile            = document.getElementById('bir_file');
            if (businessName)       businessName.required       = true;
            if (businessType)       businessType.required       = true;
            if (sellerIdType)       sellerIdType.required       = true;
            if (sellerIdNumber)     sellerIdNumber.required     = true;
            if (sellerIdFile)       sellerIdFile.required       = true;
            if (businessPermitFile) businessPermitFile.required = true;
            if (birFile)            birFile.required            = true;
        } else {
            sellerFields.style.display = 'none';
            const businessName       = document.getElementById('business_name');
            const businessType       = document.getElementById('business_type');
            const sellerIdType       = document.getElementById('seller_id_type');
            const sellerIdNumber     = document.getElementById('seller_id_number');
            const sellerIdFile       = document.getElementById('seller_id_file');
            const businessPermitFile = document.getElementById('business_permit_file');
            const birFile            = document.getElementById('bir_file');
            if (businessName)       businessName.required       = false;
            if (businessType)       businessType.required       = false;
            if (sellerIdType)       sellerIdType.required       = false;
            if (sellerIdNumber)     sellerIdNumber.required     = false;
            if (sellerIdFile)       sellerIdFile.required       = false;
            if (businessPermitFile) businessPermitFile.required = false;
            if (birFile)            birFile.required            = false;
        }

        // --- Rider ---
        if (role === 'rider') {
            riderFields.style.display = 'block';
            const licensedId = document.getElementById('licensed_id');
            const receipt    = document.getElementById('original_receipt');
            const cor        = document.getElementById('certificate_of_registration');
            if (licensedId) licensedId.required = true;
            if (receipt)    receipt.required     = true;
            if (cor)        cor.required         = true;
        } else {
            riderFields.style.display = 'none';
            const licensedId = document.getElementById('licensed_id');
            const receipt    = document.getElementById('original_receipt');
            const cor        = document.getElementById('certificate_of_registration');
            if (licensedId) licensedId.required = false;
            if (receipt)    receipt.required     = false;
            if (cor)        cor.required         = false;
        }
    }

    // File preview helper
    function setupFilePreview(inputId, previewId) {
        const input   = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        if (!input || !preview) return;
        input.addEventListener('change', function() {
            preview.innerHTML = '';
            if (input.files && input.files[0]) {
                const file = input.files[0];
                if (file.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    img.src = URL.createObjectURL(file);
                    img.style.cssText = 'max-width:100%;max-height:120px;border-radius:6px;border:1px solid #dee2e6;';
                    preview.appendChild(img);
                } else {
                    preview.innerHTML = `<span class="badge bg-secondary"><i class="fas fa-file-pdf me-1"></i>${file.name}</span>`;
                }
            }
        });
    }
    setupFilePreview('licensed_id', 'licensed_id_preview');
    setupFilePreview('original_receipt', 'original_receipt_preview');
    setupFilePreview('certificate_of_registration', 'certificate_of_registration_preview');

    // Role radio button listeners
    document.querySelectorAll('input[name="role"]').forEach(function(radio) {
        radio.addEventListener('change', toggleRoleFields);
    });

    // Form + modal setup
    const form              = document.getElementById('registrationForm');
    const confirmationModal = new bootstrap.Modal(document.getElementById('confirmationModal'));
    const confirmationForm  = document.getElementById('confirmationForm');
    const resendCodeBtn     = document.getElementById('resendCodeBtn');

    let savedFormData = null;

    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const formData        = new FormData(form);
            const email           = formData.get('email');
            const password        = formData.get('password');
            const confirmPassword = formData.get('confirm_password');

            if (!email || !password || !confirmPassword) {
                alert('Please fill in all required fields.');
                return;
            }

            const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{};:'"|<>?,./`~]).{8,}$/;
            if (!passwordPattern.test(password)) {
                alert('Password must contain at least one lowercase letter, one uppercase letter, one number, one special character, and be at least 8 characters long.');
                return;
            }
            if (password !== confirmPassword) {
                alert('Passwords do not match!');
                return;
            }

            const phone = formData.get('phone') || '';
            if (!/^[0-9]{11}$/.test(phone)) {
                alert('Phone number must be exactly 11 digits with no letters or spaces (e.g. 09123456789).');
                return;
            }

            const postalCode = formData.get('postal_code') || '';
            if (!/^[0-9]{4}$/.test(postalCode)) {
                alert('Postal code must be exactly 4 digits (e.g. 1000).');
                return;
            }

            sendConfirmationCode(email, formData);
        });
    }

    if (confirmationForm) {
        confirmationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const confirmationCode = document.getElementById('confirmation_code').value;
            const email            = document.getElementById('email').value;
            if (!confirmationCode || confirmationCode.length !== 6) {
                alert('Please enter a valid 6-digit confirmation code.');
                return;
            }
            verifyCodeAndCreateAccount(email, confirmationCode);
        });
    }

    if (resendCodeBtn) {
        resendCodeBtn.addEventListener('click', function() {
            const email = document.getElementById('email').value;
            if (!email) { alert('Please enter your email address first.'); return; }
            resendConfirmationCode(email);
        });
    }

    function sendConfirmationCode(email, formData) {
        savedFormData = formData;
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending Code...';
        submitBtn.disabled  = true;

        fetch('/auth/register', { method: 'POST', body: formData })
        .then(function(response) {
            if (!response.ok) throw new Error('HTTP error! status: ' + response.status);
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                confirmationModal.show();
                submitBtn.innerHTML = '<i class="fas fa-user-plus me-2"></i>Create Account';
                submitBtn.disabled  = false;
            } else {
                alert('Error: ' + (data.message || 'Failed to send confirmation code. Please try again.'));
                submitBtn.innerHTML = '<i class="fas fa-user-plus me-2"></i>Create Account';
                submitBtn.disabled  = false;
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('An error occurred while sending confirmation code. Please try again.');
            submitBtn.innerHTML = '<i class="fas fa-user-plus me-2"></i>Create Account';
            submitBtn.disabled  = false;
        });
    }

    function verifyCodeAndCreateAccount(email, confirmationCode) {
        const verifyBtn = confirmationForm.querySelector('button[type="submit"]');
        verifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Verifying...';
        verifyBtn.disabled  = true;

        fetch('/auth/api/verify-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, confirmation_code: confirmationCode })
        })
        .then(function(response) {
            if (!response.ok) throw new Error('HTTP error! status: ' + response.status);
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                const formData = savedFormData || new FormData(form);
                formData.set('email_verified', 'true');
                fetch('/auth/register', { method: 'POST', body: formData })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.success) {
                        alert('Account created successfully! Please login.');
                        window.location.href = '/auth/login';
                    } else {
                        alert('Registration failed: ' + (data.message || 'Please try again.'));
                        verifyBtn.innerHTML = '<i class="fas fa-check me-2"></i>Verify & Create Account';
                        verifyBtn.disabled  = false;
                    }
                })
                .catch(function(error) {
                    console.error('Error:', error);
                    alert('Registration failed. Please try again.');
                    verifyBtn.innerHTML = '<i class="fas fa-check me-2"></i>Verify & Create Account';
                    verifyBtn.disabled  = false;
                });
            } else {
                alert('Invalid confirmation code. Please try again.');
                verifyBtn.innerHTML = '<i class="fas fa-check me-2"></i>Verify & Create Account';
                verifyBtn.disabled  = false;
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('Verification failed. Please try again.');
            verifyBtn.innerHTML = '<i class="fas fa-check me-2"></i>Verify & Create Account';
            verifyBtn.disabled  = false;
        });
    }

    function resendConfirmationCode(email) {
        resendCodeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending...';
        resendCodeBtn.disabled  = true;
        fetch('/auth/resend-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.success) {
                alert('Confirmation code resent to your email.');
            } else {
                alert('Failed to resend code. Please try again.');
            }
        })
        .catch(function(error) {
            console.error('Error:', error);
            alert('Failed to resend code. Please try again.');
        })
        .finally(function() {
            resendCodeBtn.innerHTML = '<i class="fas fa-redo me-2"></i>Resend Code';
            resendCodeBtn.disabled  = false;
        });
    }
});
