/**
 * api.js — PeakForm API fetch wrapper
 */

const API_BASE = '';

async function apiFetch(url, options = {}, showLoad = true) {
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

    if (res.status === 401) {
      clearAuth();
      window.location.href = '/login.html';
      return { _error: true, status: 401 };
    }

    if (!res.ok) {
      const msg = data?.error || data?.message || `HTTP ${res.status}`;
      showToast(msg, 'error');
      return { _error: true, status: res.status, message: msg, ...data };
    }

    return data;
  } catch (e) {
    showToast('Network error — is the server running?', 'error');
    return { _error: true, message: e.message };
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
    showToast('Upload failed: ' + e.message, 'error');
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
