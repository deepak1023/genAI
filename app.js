const form = document.querySelector('#chatForm');
const input = document.querySelector('#messageInput');
const chatScroll = document.querySelector('#chatScroll');
const newChatButton = document.querySelector('#newChatButton');
const quickPrompts = document.querySelectorAll('[data-prompt]');

// Use the same origin when served by server.py; otherwise (file://, Live Server, ...)
// talk to server.py directly.
const API_URL = location.protocol.startsWith('http') && location.port === '8000'
  ? '/api/chat'
  : 'http://127.0.0.1:8000/api/chat';

// Conversation sent to the server on every turn (the greeting is UI-only).
let history = [];
let busy = false;

function addMessage(text, sender) {
  const row = document.createElement('div');
  row.className = `message-row ${sender === 'user' ? 'user-row' : 'assistant-row'}`;
  row.innerHTML = sender === 'user'
    ? `<div class="message-stack"><div class="message-meta"><strong>You</strong><time>now</time></div><div class="message user-message"></div></div>`
    : `<div class="mini-avatar" aria-hidden="true">✦</div><div class="message-stack"><div class="message-meta"><strong>Orchid</strong><time>now</time></div><div class="message assistant-message"></div></div>`;
  row.querySelector('.message').textContent = text;
  chatScroll.appendChild(row);
  chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: 'smooth' });
  return row;
}

function scrollToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

async function fetchReply(bubble) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: history }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `Server error (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let text = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    text += decoder.decode(value, { stream: true });
    bubble.classList.remove('typing');
    bubble.textContent = text;
    scrollToBottom();
  }
  return text;
}

async function sendMessage(text) {
  const cleanText = text.trim();
  if (!cleanText || busy) return;
  busy = true;
  addMessage(cleanText, 'user');
  history.push({ role: 'user', content: cleanText });
  input.value = '';
  input.style.height = 'auto';

  const row = addMessage('', 'assistant');
  const bubble = row.querySelector('.message');
  bubble.classList.add('typing');
  bubble.innerHTML = '<i></i><i></i><i></i>';

  try {
    const reply = await fetchReply(bubble);
    if (reply) {
      history.push({ role: 'assistant', content: reply });
    } else {
      throw new Error('Empty response.');
    }
  } catch (error) {
    history.pop(); // drop the unanswered user turn so history stays valid
    bubble.classList.remove('typing');
    bubble.textContent = error instanceof TypeError
      ? 'Could not reach the server. Is `python server.py` running?'
      : error.message;
  } finally {
    busy = false;
    input.focus();
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  sendMessage(input.value);
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage(input.value);
  }
});

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = `${Math.min(input.scrollHeight, 100)}px`;
});

quickPrompts.forEach((button) => {
  button.addEventListener('click', () => sendMessage(button.dataset.prompt));
});

newChatButton.addEventListener('click', () => {
  if (busy) return;
  history = [];
  // Keep the greeting (first assistant row); remove everything added after it.
  const rows = chatScroll.querySelectorAll('.message-row');
  rows.forEach((row, index) => { if (index > 0) row.remove(); });
  input.focus();
});
