/**
 * chat.js — PeakForm Real-time chat using Socket.IO
 * Focused on Community Groups and PeakForm interactions.
 */

let socket = null;
let currentRoomId = null;
let myNickname = '';
const myUserId = getUser()?.user_id;
const myRole   = getUser()?.role;

// ============================================================
// Group Chat (community-chat.html)
// ============================================================

async function initCommunityChat() {
  requireAuth();
  renderSidebar();
  initMobileSidebar();

  const params = new URLSearchParams(window.location.search);
  currentRoomId = parseInt(params.get('room'));
  
  if (!currentRoomId) {
      // If we are on the main chat page without a room, we just load the rooms list
      // which is handled by the inline script in community-chat.html
      return; 
  }

  // Load room history or info if needed (most logic is in community-chat.html)
  // This script provides core socket connectivity helpers.
  if (!socket) connectSocket();
}

function connectSocket() {
  if (socket) return;

  socket = io(window.location.origin, {
    transports: ['websocket', 'polling'],
  });

  socket.on('connect', () => {
    console.log('[PeakForm Socket] Connected');
  });

  socket.on('connect_error', (err) => {
    console.warn('[PeakForm Socket] Connection error:', err.message);
  });
}

// ============================================================
// Helpers
// ============================================================

function scrollToBottom(containerId = 'chat-messages') {
  const container = document.getElementById(containerId);
  if (container) container.scrollTop = container.scrollHeight;
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ============================================================
// Page Init
// ============================================================
onReady(() => {
  const path = window.location.pathname;
  if (path.includes('community-chat')) {
    initCommunityChat();
  }
});
