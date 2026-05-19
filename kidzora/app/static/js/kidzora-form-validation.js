/* ══════════════════════════════════════════════════════════════
   kidzora-form-validation.js
   Real-time form validation and error feedback utilities
═════════════════════════════════════════════════════════════ */

console.log('[LOAD] kidzora-form-validation.js is loading...');

/**
 * Validation rules and patterns
 */
window.VALIDATION_RULES = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  password: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[a-zA-Z\d@$!%*?&]/,
  phone: /^(\+63|0)[0-9]{10}$/,
  url: /^https?:\/\/.+\..+/i,
  alphanumeric: /^[a-zA-Z0-9]+$/,
  username: /^[a-zA-Z0-9_-]{3,20}$/,
};

/**
 * Validate email format
 * @param {string} email - Email address to validate
 * @returns {boolean}
 */
window.isValidEmail = function (email) {
  return VALIDATION_RULES.email.test(email);
};

/**
 * Validate password strength (min 8 chars, 1 uppercase, 1 lowercase, 1 number, 1 special char)
 * @param {string} password - Password to validate
 * @returns {object} - { isValid: boolean, strength: 'weak'|'fair'|'good'|'strong', score: 0-4 }
 */
window.validatePassword = function (password) {
  var score = 0;
  var strength = 'weak';

  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[@$!%*?&#^()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) score++;

  if (score <= 1) strength = 'weak';
  else if (score === 2) strength = 'fair';
  else if (score === 3) strength = 'good';
  else strength = 'strong';

  return {
    isValid: password.length >= 8 && /[A-Z]/.test(password) && /[0-9]/.test(password),
    strength: strength,
    score: Math.min(4, score),
  };
};

/**
 * Validate field value against rules
 * @param {string} value - Value to validate
 * @param {object} rules - Validation rules { type: 'email'|'password'|'required'|etc., min, max, ... }
 * @returns {object} - { isValid: boolean, error: string }
 */
window.validateField = function (value, rules) {
  if (!rules) return { isValid: true };

  var result = { isValid: true, error: '' };

  // Check required
  if (rules.required && (!value || value.trim() === '')) {
    result.isValid = false;
    result.error = 'This field is required';
    return result;
  }

  if (!value) return result; // No other checks if empty and not required

  // Check email
  if (rules.type === 'email' && !isValidEmail(value)) {
    result.isValid = false;
    result.error = 'Please enter a valid email address';
    return result;
  }

  // Check password
  if (rules.type === 'password') {
    var pwResult = validatePassword(value);
    if (!pwResult.isValid) {
      result.isValid = false;
      result.error = 'Password must be at least 8 chars with uppercase, number, and special character';
      return result;
    }
  }

  // Check min length
  if (rules.minLength && value.length < rules.minLength) {
    result.isValid = false;
    result.error = 'Minimum ' + rules.minLength + ' characters required';
    return result;
  }

  // Check max length
  if (rules.maxLength && value.length > rules.maxLength) {
    result.isValid = false;
    result.error = 'Maximum ' + rules.maxLength + ' characters allowed';
    return result;
  }

  // Check pattern
  if (rules.pattern) {
    var patternRegex = typeof rules.pattern === 'string' ? new RegExp(rules.pattern) : rules.pattern;
    if (!patternRegex.test(value)) {
      result.isValid = false;
      result.error = rules.patternError || 'Invalid format';
      return result;
    }
  }

  // Check match (for password confirmation, etc.)
  if (rules.match && value !== rules.match) {
    result.isValid = false;
    result.error = rules.matchError || 'Fields do not match';
    return result;
  }

  // Check custom validator
  if (rules.custom && typeof rules.custom === 'function') {
    var customResult = rules.custom(value);
    if (customResult !== true) {
      result.isValid = false;
      result.error = customResult || 'Invalid value';
      return result;
    }
  }

  return result;
};

/**
 * Mark field as invalid and show error message
 * @param {HTMLElement} field - Input field element
 * @param {string} errorMessage - Error message to display
 */
window.markFieldInvalid = function (field, errorMessage) {
  if (!field) return;

  field.classList.remove('is-valid');
  field.classList.add('is-invalid');

  // Find or create error message container
  var errorContainer = field.parentElement.querySelector('.invalid-feedback');
  if (!errorContainer) {
    errorContainer = document.createElement('div');
    errorContainer.className = 'invalid-feedback';
    field.parentElement.appendChild(errorContainer);
  }

  errorContainer.textContent = errorMessage;
  errorContainer.style.display = 'block';

  // Update form group state
  if (field.closest('.form-group')) {
    field.closest('.form-group').classList.add('has-error');
    field.closest('.form-group').classList.remove('has-success');
  }
};

/**
 * Mark field as valid
 * @param {HTMLElement} field - Input field element
 * @param {string} [successMessage] - Optional success message
 */
window.markFieldValid = function (field, successMessage) {
  if (!field) return;

  field.classList.remove('is-invalid');
  field.classList.add('is-valid');

  // Hide error message if exists
  var errorContainer = field.parentElement.querySelector('.invalid-feedback');
  if (errorContainer) {
    errorContainer.style.display = 'none';
  }

  // Show success message if provided
  if (successMessage) {
    var successContainer = field.parentElement.querySelector('.valid-feedback');
    if (!successContainer) {
      successContainer = document.createElement('div');
      successContainer.className = 'valid-feedback';
      field.parentElement.appendChild(successContainer);
    }
    successContainer.textContent = successMessage;
    successContainer.style.display = 'block';
  }

  // Update form group state
  if (field.closest('.form-group')) {
    field.closest('.form-group').classList.add('has-success');
    field.closest('.form-group').classList.remove('has-error');
  }
};

/**
 * Clear field validation state
 * @param {HTMLElement} field - Input field element
 */
window.clearFieldValidation = function (field) {
  if (!field) return;

  field.classList.remove('is-valid', 'is-invalid');

  var errorContainer = field.parentElement.querySelector('.invalid-feedback');
  if (errorContainer) errorContainer.style.display = 'none';

  var successContainer = field.parentElement.querySelector('.valid-feedback');
  if (successContainer) successContainer.style.display = 'none';

  if (field.closest('.form-group')) {
    field.closest('.form-group').classList.remove('has-error', 'has-success');
  }
};

/**
 * Setup real-time validation on a field
 * @param {HTMLElement|string} field - Input field element or selector
 * @param {object} rules - Validation rules
 * @param {Function} [onValidChange] - Callback when validation state changes
 */
window.setupValidation = function (field, rules, onValidChange) {
  field = typeof field === 'string' ? document.querySelector(field) : field;
  if (!field) return;

  var validate = function () {
    var result = validateField(field.value, rules);

    if (result.isValid) {
      markFieldValid(field);
      if (onValidChange) onValidChange(true);
    } else {
      markFieldInvalid(field, result.error);
      if (onValidChange) onValidChange(false);
    }
  };

  // Real-time validation on input
  field.addEventListener('blur', validate);
  field.addEventListener('input', function () {
    if (field.classList.contains('is-invalid')) {
      validate();
    }
  });

  return validate;
};

console.log('[READY] window.setupValidation is now available:', typeof window.setupValidation);

/**
 * Setup password strength meter
 * @param {HTMLElement|string} passwordField - Password input field
 * @param {HTMLElement|string} [meterContainer] - Container for strength meter
 */
window.setupPasswordMeter = function (passwordField, meterContainer) {
  passwordField = typeof passwordField === 'string'
    ? document.querySelector(passwordField)
    : passwordField;

  if (!passwordField) return;

  var meter = meterContainer
    ? (typeof meterContainer === 'string'
      ? document.querySelector(meterContainer)
      : meterContainer)
    : null;

  var updateMeter = function () {
    var result = validatePassword(passwordField.value);

    if (meter) {
      // Update strength meter bars
      var bars = meter.querySelectorAll('.password-strength-meter__bar');
      bars.forEach(function (bar, index) {
        if (index < result.score) {
          bar.className = 'password-strength-meter__bar ' + result.strength;
        } else {
          bar.className = 'password-strength-meter__bar';
        }
      });

      // Update strength text
      var textEl = meter.querySelector('.password-strength-text');
      if (textEl) {
        textEl.className = 'password-strength-text ' + result.strength;
        textEl.textContent = result.strength;
      }
    }
  };

  passwordField.addEventListener('input', updateMeter);
  return updateMeter;
};

/**
 * Setup character counter for textarea/input
 * @param {HTMLElement|string} field - Input/textarea element
 * @param {HTMLElement|string} counterContainer - Counter display container
 */
window.setupCharCounter = function (field, counterContainer) {
  field = typeof field === 'string' ? document.querySelector(field) : field;
  counterContainer = typeof counterContainer === 'string'
    ? document.querySelector(counterContainer)
    : counterContainer;

  if (!field || !counterContainer) return;

  var maxLength = field.getAttribute('maxlength') || field.maxLength;
  if (!maxLength) return;

  var updateCounter = function () {
    var remaining = maxLength - field.value.length;
    var percentage = (field.value.length / maxLength) * 100;

    var remainingEl = counterContainer.querySelector('.char-counter__remaining');
    if (remainingEl) {
      remainingEl.textContent = remaining + ' remaining';

      // Update warning/danger state
      remainingEl.classList.remove('warning', 'danger');
      if (percentage >= 90) remainingEl.classList.add('danger');
      else if (percentage >= 75) remainingEl.classList.add('warning');
    }
  };

  field.addEventListener('input', updateCounter);
  updateCounter(); // Initial update

  return updateCounter;
};

/**
 * Validate entire form and show all errors
 * @param {HTMLElement|string} form - Form element
 * @returns {boolean} - True if form is valid
 */
window.validateForm = function (form) {
  form = typeof form === 'string' ? document.querySelector(form) : form;
  if (!form) return false;

  var isValid = true;
  
  // Get fields with data-validate OR required attribute
  var fields = form.querySelectorAll(
    'input[data-validate], textarea[data-validate], select[data-validate], input[required], textarea[required], select[required]'
  );

  console.log('[VALIDATE] Checking ' + fields.length + ' fields');

  fields.forEach(function (field) {
    try {
      var rulesJson = field.getAttribute('data-validate');
      var rules = rulesJson ? JSON.parse(rulesJson) : {};
      rules.required = field.hasAttribute('required');

      var result = validateField(field.value, rules);

      if (result.isValid) {
        markFieldValid(field);
      } else {
        console.log('[VALIDATE] Field error: ' + (field.name || field.id) + ' - ' + result.error);
        markFieldInvalid(field, result.error);
        isValid = false;
      }
    } catch (err) {
      console.error('[VALIDATE] Error validating field:', err);
      isValid = false;
    }
  });

  // Add shake animation if form has errors
  if (!isValid) {
    console.log('[VALIDATE] Form has errors');
    form.classList.add('has-errors');
    setTimeout(function () {
      form.classList.remove('has-errors');
    }, 500);
  } else {
    console.log('[VALIDATE] Form is valid');
  }

  return isValid;
};

/**
 * Reset form validation state (clear all errors/success states)
 * @param {HTMLElement|string} form - Form element
 */
window.resetFormValidation = function (form) {
  form = typeof form === 'string' ? document.querySelector(form) : form;
  if (!form) return;

  var fields = form.querySelectorAll('input, textarea, select');
  fields.forEach(function (field) {
    clearFieldValidation(field);
  });

  form.classList.remove('has-errors');
};

/**
 * Setup form submit with validation
 * @param {HTMLElement|string} form - Form element
 * @param {Function} onSubmit - Callback if form is valid (receives event)
 * @returns {Function} - Unbind function
 */
window.setupFormSubmit = function (form, onSubmit) {
  form = typeof form === 'string' ? document.querySelector(form) : form;
  if (!form) return function () {};

  var handleSubmit = function (e) {
    e.preventDefault();
    console.log('[FORM] Submitting form, validating...');

    try {
      if (validateForm(form)) {
        console.log('[FORM] Validation passed, calling onSubmit');
        if (onSubmit) onSubmit(e);
        else {
          console.log('[FORM] No callback, submitting form directly');
          form.submit();
        }
      } else {
        console.log('[FORM] Validation failed, preventing submission');
      }
    } catch (err) {
      console.error('[FORM] Error during submission:', err);
      alert('An error occurred. Please try again.');
    }
  };

  form.addEventListener('submit', handleSubmit);

  return function () {
    form.removeEventListener('submit', handleSubmit);
  };
};

/**
 * Show loading state on submit button
 * @param {HTMLElement|string} button - Submit button element
 * @param {string} [loadingText] - Text to show while loading
 */
window.setButtonLoading = function (button, loadingText) {
  button = typeof button === 'string' ? document.querySelector(button) : button;
  if (!button) return;

  button.dataset.originalText = button.textContent;
  button.dataset.originalHtml = button.innerHTML;

  if (loadingText) {
    button.textContent = loadingText;
  }

  button.disabled = true;
  button.classList.add('is-loading');
};

/**
 * Clear loading state on submit button
 * @param {HTMLElement|string} button - Submit button element
 */
window.clearButtonLoading = function (button) {
  button = typeof button === 'string' ? document.querySelector(button) : button;
  if (!button) return;

  button.disabled = false;
  button.classList.remove('is-loading');

  if (button.dataset.originalHtml) {
    button.innerHTML = button.dataset.originalHtml;
  } else if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
  }
};

/**
 * Check if email already exists (via API call)
 * @param {string} email - Email to check
 * @param {string} endpoint - API endpoint to call
 * @returns {Promise<boolean>} - True if email is available
 */
window.checkEmailAvailable = function (email, endpoint) {
  return fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email }),
  })
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      return data.available !== false;
    })
    .catch(function () {
      return true;
    });
};

/* ══════════════════════════════════════════════════════════════
   Usage Patterns:

   1. HTML with data-validate attribute:
   <form>
     <input type="email" name="email" data-validate='{"type":"email","required":true}' required>
     <input type="password" name="password" data-validate='{"type":"password"}' required>
     <button type="submit">Submit</button>
   </form>

   2. Validate form on submit:
   window.setupFormSubmit('form', function() {
     console.log('Form is valid!');
   });

   3. Real-time validation on specific field:
   window.setupValidation('.email-field', { 
     type: 'email', 
     required: true 
   });

   4. Password strength meter:
   window.setupPasswordMeter('.password-field', '.strength-meter');

   5. Character counter:
   window.setupCharCounter('.bio-field', '.char-counter');

   6. Custom validation:
   window.setupValidation('.username', {
     custom: function(value) {
       return value.length >= 3 ? true : 'Username must be 3+ chars';
     }
   });
═════════════════════════════════════════════════════════════ */

console.log('[LOADED] kidzora-form-validation.js FULLY LOADED. All validation functions available.');
