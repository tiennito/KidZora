/**
 * KidZora – Auth / Register Fixed (Complete Registration Form)
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing registration form...');

    // Toggle seller fields based on account type
    function toggleAccountType() {
        const role         = document.getElementById('role').value;
        const sellerFields = document.getElementById('sellerFields');

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
    }

    // File preview functionality
    function setupFilePreview(inputId, previewId) {
        const input   = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        if (input && preview) {
            input.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        if (file.type.startsWith('image/')) {
                            preview.innerHTML = '<img src="' + e.target.result + '" alt="Preview" class="img-thumbnail" style="max-width: 200px; max-height: 150px;">' +
                                               '<div class="small text-muted">' + file.name + '</div>';
                            preview.style.display = 'block';
                        } else {
                            preview.innerHTML = '<div class="alert alert-info">' +
                                               '<i class="fas fa-file-pdf me-2"></i>' +
                                               file.name + ' (PDF Document)' +
                                               '</div>';
                            preview.style.display = 'block';
                        }
                    };
                    reader.readAsDataURL(file);
                } else {
                    preview.style.display = 'none';
                }
            });
        }
    }

    // Setup file previews
    setupFilePreview('seller_id_file', 'seller_id_preview');
    setupFilePreview('business_permit_file', 'business_permit_preview');
    setupFilePreview('bir_file', 'bir_preview');

    // Make toggle function global
    window.toggleAccountType = toggleAccountType;

    // Form validation
    const form = document.getElementById('registrationForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password        = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            if (password !== confirmPassword) {
                e.preventDefault();
                alert('Passwords do not match!');
                return false;
            }

            const buildingNumber = document.getElementById('building_number').value;
            const streetName     = document.getElementById('street_name').value;
            if (!buildingNumber || !streetName) {
                e.preventDefault();
                alert('Please enter both building number and street name!');
                return false;
            }

            const region   = document.getElementById('region').value;
            const province = document.getElementById('province').value;
            const city     = document.getElementById('city').value;
            const barangay = document.getElementById('barangay').value;
            if (!region || !province || !city || !barangay) {
                e.preventDefault();
                alert('Please complete all location fields!');
                return false;
            }

            const role = document.getElementById('role').value;
            if (role === 'seller') {
                const businessName       = document.getElementById('business_name');
                const businessType       = document.getElementById('business_type');
                const sellerIdType       = document.getElementById('seller_id_type');
                const sellerIdNumber     = document.getElementById('seller_id_number');
                const sellerIdFile       = document.getElementById('seller_id_file');
                const businessPermitFile = document.getElementById('business_permit_file');
                const birFile            = document.getElementById('bir_file');
                if (!businessName || !businessType || !sellerIdType || !sellerIdNumber ||
                    !sellerIdFile || !businessPermitFile || !birFile ||
                    !businessName.value || !businessType.value || !sellerIdType.value || !sellerIdNumber.value ||
                    (sellerIdFile.files && sellerIdFile.files.length === 0) ||
                    (businessPermitFile.files && businessPermitFile.files.length === 0) ||
                    (birFile.files && birFile.files.length === 0)) {
                    e.preventDefault();
                    alert('Please complete all seller business information fields!');
                    return false;
                }
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Creating Account...';
            submitBtn.disabled  = true;
            setTimeout(function() {
                submitBtn.innerHTML = '<i class="fas fa-user-plus me-2"></i>Create Account';
                submitBtn.disabled  = false;
            }, 3000);
        });
    }
});
