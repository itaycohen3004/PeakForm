/**
 * auth.js — PeakForm Authentication Logic
 * Handles Login, Registration, and Password management.
 * Strictly Athlete/Admin roles. No medical leftovers.
 */

// ============================================================
// LOGIN
// ============================================================

async function handleLogin(e) {
  e.preventDefault();
  const form = e.target;
  clearFieldErrors(form);

  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  if (!email || !password) {
    showToast('Please enter your email and password.', 'warning');
    return;
  }

  const btn = form.querySelector('[type="submit"]');
  btn.classList.add('loading');
  btn.disabled = true;

  const data = await apiFetch('/api/auth/login', {
    method: 'POST',
    body: { email, password },
  }, false);

  btn.classList.remove('loading');
  btn.disabled = false;

  if (!data) return;

  if (data._error) {
    const msg = data.error || 'Login failed.';
    showToast(msg, 'error');
    if (data.errors) showFieldErrors(data.errors);
    return;
  }

  // Save auth data
  saveAuth(data.token, {
    user_id: data.user_id,
    role: data.role,
    email: data.email,
    display_name: data.display_name,
  });

  showToast('Login successful! Welcome back.', 'success');
  
  // Redirect based on role and onboarding status
  setTimeout(() => {
    if (data.role === 'athlete' && !data.onboarding_complete) {
        window.location.href = '/onboarding.html';
    } else {
        window.location.href = getDashboardUrl(data.role);
    }
  }, 800);
}

// ============================================================
// REGISTER
// ============================================================

async function handleRegister(e) {
  e.preventDefault();
  const form = e.target;
  clearFieldErrors(form);

  const payload = {
    email:        document.getElementById('email').value.trim(),
    password:     document.getElementById('password').value,
    display_name: document.getElementById('display_name')?.value.trim() || '',
    training_type: document.getElementById('training_type')?.value || 'gym',
  };

  // Confirm password
  const confirm = document.getElementById('confirm_password')?.value;
  if (confirm && confirm !== payload.password) {
    showFieldErrors({ confirm_password: 'Passwords do not match.' });
    return;
  }

  const btn = form.querySelector('[type="submit"]');
  btn.classList.add('loading');
  btn.disabled = true;

  const data = await apiFetch('/api/auth/register', {
    method: 'POST',
    body: payload,
  }, false);

  btn.classList.remove('loading');
  btn.disabled = false;

  if (!data) return;

  if (data._error) {
    if (data.errors) showFieldErrors(data.errors);
    else showToast(data.error || 'Registration failed.', 'error');
    return;
  }

  // Registration successful - auto login or redirect to login
  showToast('Account created! Logging you in...', 'success');
  
  saveAuth(data.token, {
    user_id: data.user_id,
    role: data.role,
    email: data.email,
    display_name: data.display_name,
  });

  setTimeout(() => {
    window.location.href = '/onboarding.html';
  }, 1200);
}

// ============================================================
// UI HELPERS
// ============================================================

function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁️';
  }
}

function updateStrength(password) {
  const bar = document.getElementById('strength-bar');
  const label = document.getElementById('strength-label');
  if (!bar) return;

  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const levels = [
    { label: '', color: '' },
    { label: 'Weak', color: 'var(--danger)' },
    { label: 'Fair', color: 'var(--warning)' },
    { label: 'Good', color: 'var(--info)' },
    { label: 'Strong', color: 'var(--success)' },
  ];

  const level = levels[score];
  bar.style.width = `${(score / 4) * 100}%`;
  bar.style.background = level.color;
  if (label) {
    label.textContent = level.label;
    label.style.color = level.color;
  }
}
