/**
 * KidZora – Auth / Register Step 1 (Account Type Selection)
 */
function selectAccountType(type) {
    // Add loading animation
    event.currentTarget.classList.add('pulse-animation');

    // Store selected type
    localStorage.setItem('selectedAccountType', type);

    // Remove previous selection
    document.querySelectorAll('.account-type-card').forEach(function(card) {
        card.classList.remove('selected');
    });

    // Add selection to clicked card
    event.currentTarget.classList.add('selected');

    // Add ripple effect
    createRipple(event);

    // Redirect after animation
    setTimeout(function() {
        window.location.href = '/auth/register/terms?type=' + type;
    }, 600);
}

function createRipple(event) {
    const card   = event.currentTarget;
    const ripple = document.createElement('div');
    ripple.className             = 'ripple';
    ripple.style.position        = 'absolute';
    ripple.style.borderRadius    = '50%';
    ripple.style.background      = 'rgba(255,255,255,0.5)';
    ripple.style.width           = ripple.style.height = '40px';
    ripple.style.left            = (event.clientX - card.offsetLeft - 20) + 'px';
    ripple.style.top             = (event.clientY - card.offsetTop  - 20) + 'px';
    ripple.style.animation       = 'ripple 0.6s ease-out';
    ripple.style.opacity         = '0';

    card.appendChild(ripple);
    setTimeout(function() { ripple.style.opacity = '1'; }, 10);
    setTimeout(function() { ripple.style.opacity = '0'; }, 300);
    setTimeout(function() {
        if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
    }, 610);
}
