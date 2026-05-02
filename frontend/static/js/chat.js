/**
 * chat.js — צ'אט הקהילה של PeakForm (בזמן אמת!)
 * הקובץ הזה אחראי לחבר את הדפדפן שלך לשרת של הצ'אט כדי שתוכל 
 * לקבל ולשלוח הודעות באופן מיידי מבלי לרענן את העמוד (בעזרת טכנולוגיה שנקראת Socket.IO).
 */

let socket = null; // משתנה שישמור את "הצינור" (החיבור) בינינו לבין השרת
let currentRoomId = null; // איזה חדר צ'אט אנחנו נמצאים בו עכשיו (למשל, חדר מספר 2)
let myNickname = ''; // השם שלי בצ'אט
const myUserId = getUser()?.user_id; // המספר המזהה שלי
const myRole   = getUser()?.role; // התפקיד שלי (מנהל או מתאמן רגיל)

// ============================================================
// אזור הצ'אט הקבוצתי (קהילה)
// ============================================================

// פונקציה שמפעילה את הצ'אט ברגע שנכנסים לעמוד
async function initCommunityChat() {
  requireAuth(); // בודקים שאתה מחובר לחשבון
  renderSidebar(); // טוענים את התפריט בצד
  initMobileSidebar(); // מסדרים את התפריט לטלפון

  // מחפשים בשורת הכתובת (URL) את המילה "room=" כדי לדעת לאיזה חדר נכנסנו
  const params = new URLSearchParams(window.location.search);
  currentRoomId = parseInt(params.get('room'));
  
  if (!currentRoomId) {
      // אם לא נכנסנו לחדר ספציפי, אנחנו רק מציגים את רשימת החדרים
      return; 
  }

  // אם אנחנו בתוך חדר ועדיין לא התחברנו לשרת, נתחבר עכשיו!
  if (!socket) connectSocket();
}

// הפונקציה שמתחברת פיזית לשרת של הצ'אט
function connectSocket() {
  if (socket) return; // אם אנחנו כבר מחוברים, אין צורך להתחבר שוב

  // מבקשים מהשרת "לפתוח קו" ולדבר איתנו בזמן אמת (websocket)
  socket = io(window.location.origin, {
    transports: ['websocket', 'polling'],
  });

  // ברגע שהצלחנו להתחבר - נדפיס הודעה סודית למתכנתים
  socket.on('connect', () => {
    console.log('[PeakForm Socket] Connected'); // התחברנו בהצלחה!
  });

  // אם יש שגיאה בחיבור, נדפיס אזהרה
  socket.on('connect_error', (err) => {
    console.warn('[PeakForm Socket] Connection error:', err.message);
  });
}

// ============================================================
// פונקציות עזר (כלים שעוזרים לנו)
// ============================================================

// פונקציה שלוקחת את המסך וגוללת למטה כדי שתמיד נראה את ההודעה הכי חדשה
function scrollToBottom(containerId = 'chat-messages') {
  const container = document.getElementById(containerId);
  if (container) container.scrollTop = container.scrollHeight;
}

// פונקציה חשובה שמגינה עלינו מהאקרים!
// היא לוקחת טקסט והופכת אותו ל"בטוח" כדי שאי אפשר יהיה להפעיל עלינו קוד זדוני דרך הודעה בצ'אט
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ============================================================
// כשהעמוד מסיים להיטען
// ============================================================
onReady(() => {
  // אם אנחנו נמצאים בדף שנקרא "community-chat", תפעיל את הפונקציה המרכזית
  const path = window.location.pathname;
  if (path.includes('community-chat')) {
    initCommunityChat();
  }
});

/*
English Summary:
This file provides the client-side Socket.IO logic for real-time community chat. It establishes 
and manages the WebSocket connection with the backend server, determines which chat room the user 
is currently viewing from the URL parameters, and includes utility functions to sanitize HTML 
input to prevent XSS attacks and automatically scroll to the newest message.

סיכום בעברית:
קובץ זה מפעיל את מסך הצ'אט הקהילתי של האתר! הוא אחראי על תקשורת חיה (WebSockets)
מול השרת - כלומר, כל הודעה שנשלחת מופיעה מיד אצל כולם בלי צורך לרענן את העמוד. 
הוא מזהה באיזה חדר צ'אט אנחנו נמצאים, ומוודא שמשתמשים לא יוכלו להכניס קוד זדוני לתוך ההודעות (XSS).
*/
