/**
 * api.js — PeakForm API fetch wrapper
 */

const API_BASE = '';

/**
 * apiFetch — wraps fetch with auth headers, error handling and loading UI.
 *
 * options (beyond standard fetch options):
 *   showLoad         {boolean}  show global loading spinner (3rd positional arg, default true)
 *   silent           {boolean}  suppress the automatic showToast on error (default false)
 *   skipAuthRedirect {boolean}  do NOT redirect to /login.html on 401 (use on login/register pages)
 */
async function apiFetch(url, options = {}, showLoad = true) {
  const silent           = options.silent           ?? false;
  const skipAuthRedirect = options.skipAuthRedirect ?? false;

  if (showLoad) showLoading();
  try {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(API_BASE + url, {
      ...options,
      headers,
      credentials: 'include',
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { _raw: text }; }

    // 401 on protected pages → redirect to login.
    // Skip redirect on auth pages (login/register) so the error can be shown inline.
    if (res.status === 401 && !skipAuthRedirect) {
      clearAuth();
      window.location.href = '/login.html';
      return { _error: true, status: 401 };
    }

    if (!res.ok) {
      const msg = data?.error || data?.message || `HTTP ${res.status}`;
      if (!silent) showToast(msg, 'error');
      return { _error: true, status: res.status, message: msg, ...data };
    }

    return data;
  } catch (e) {
    // e.message is often the raw "Failed to fetch" — replace with a human-friendly message
    const friendly = 'Server connection error. Please try again later.';
    if (!silent) showToast(friendly, 'error');
    return { _error: true, status: 0, message: friendly };
  } finally {
    if (showLoad) hideLoading();
  }
}

async function apiUpload(url, formData) {
  showLoading('Uploading...');
  try {
    const token = getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(API_BASE + url, { 
      method: 'POST', 
      headers, 
      credentials: 'include',
      body: formData 
    });
    const data = await res.json();
    if (!res.ok) { showToast(data?.error || 'Upload failed', 'error'); return { _error: true, ...data }; }
    return data;
  } catch (e) {
    showToast('Upload failed. Please try again.', 'error');
    return { _error: true };
  } finally {
    hideLoading();
  }
}

async function apiDownload(url, filename) {
  showLoading('Downloading...');
  try {
    const token = getToken();
    const res = await fetch(API_BASE + url, { 
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include'
    });
    if (!res.ok) { showToast('Download failed', 'error'); return; }
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  } catch (e) {
    showToast('Download error', 'error');
  } finally {
    hideLoading();
  }
}
