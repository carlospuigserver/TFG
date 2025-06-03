const potSpan = document.getElementById('pot');
const playerChipsSpan = document.getElementById('playerChips');
const botChipsSpan = document.getElementById('botChips');
const dealerSpan = document.getElementById('dealerDisplay');
const toActSpan = document.getElementById('toActDisplay');

const botCardsDiv = document.getElementById('botCards');
const playerCardsDiv = document.getElementById('playerCards');
const communityCardsDiv = document.getElementById('communityCards');
const botMessageDiv = document.getElementById('botMessage');
const playerMessageDiv = document.getElementById('playerMessage');
const actionsContainer = document.getElementById('actionsContainer');
const logContainer = document.getElementById('logContainer');

let gameState = null;

function log(msg) {
  const p = document.createElement('p');
  p.textContent = msg;
  logContainer.appendChild(p);
  logContainer.scrollTop = logContainer.scrollHeight;
}

function cardToImg(card) {
  if (card === "card_back") return '<img src="card_back.png" alt="Carta Oculta" class="card">';
  const filename = card.toLowerCase() + '.png';
  return `<img src="cards/${filename}" alt="${card}" class="card">`;
}

function renderCards() {
  botCardsDiv.innerHTML = gameState.bot_hole.map(c => cardToImg(c)).join('');
  playerCardsDiv.innerHTML = gameState.player_hole.map(c => cardToImg(c)).join('');
  communityCardsDiv.innerHTML = gameState.community_cards.map(c => cardToImg(c)).join('');
}

function updateStatus() {
  potSpan.textContent = gameState.pot;
  playerChipsSpan.textContent = gameState.player_chips;
  botChipsSpan.textContent = gameState.bot_chips;
  dealerSpan.textContent = gameState.dealer;
  toActSpan.textContent = gameState.to_act || '–';
}

function clearActions() {
  actionsContainer.innerHTML = '';
  playerMessageDiv.textContent = '';
  botMessageDiv.textContent = '';
}

// Mostrar mensajes específicos al lado de cada jugador
function updatePlayerMessages(logs) {
  // Filtrar mensajes del jugador y bot
  const lastPlayerMsg = logs.slice().reverse().find(m => m.toLowerCase().startsWith("player") || m.toLowerCase().startsWith("tú"));
  const lastBotMsg = logs.slice().reverse().find(m => m.toLowerCase().startsWith("bot"));

  playerMessageDiv.textContent = lastPlayerMsg || '';
  botMessageDiv.textContent = lastBotMsg || '';
}

function enableActions(enable) {
  clearActions();
  if (!enable) return;

  playerMessageDiv.textContent = "Tu turno: elige acción.";

  const btnFold = document.createElement('button');
  btnFold.textContent = 'Fold';
  btnFold.onclick = () => sendPlayerAction('fold');

  const btnCall = document.createElement('button');
  btnCall.textContent = 'Call';
  btnCall.onclick = () => sendPlayerAction('call');

  const inputRaise = document.createElement('input');
  inputRaise.type = 'number';
  inputRaise.min = 1;
  inputRaise.placeholder = 'Cantidad raise';

  const btnRaise = document.createElement('button');
  btnRaise.textContent = 'Raise';
  btnRaise.onclick = () => {
    const val = parseInt(inputRaise.value);
    if (!val || val <= 0) {
      alert('Introduce un valor válido para raise.');
      return;
    }
    sendPlayerAction('raise', val);
  };

  actionsContainer.appendChild(btnFold);
  actionsContainer.appendChild(btnCall);
  actionsContainer.appendChild(inputRaise);
  actionsContainer.appendChild(btnRaise);
}

async function sendPlayerAction(action, raise_amount = null) {
  log(`Jugador: ${action}${raise_amount ? ' ' + raise_amount : ''}`);

  const res = await fetch('/api/player_action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({action, raise_amount})
  });
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    return;
  }

  gameState = data;
  renderCards();
  updateStatus();

  if (data.log) {
    for (const m of data.log) {
      log(m);
    }
    updatePlayerMessages(data.log);
  }

  if (data.hand_ended) {
    log('Mano terminada.');
    enableActions(false);
    playerMessageDiv.textContent = 'Mano terminada. Pulsa "Nueva Mano" para continuar.';
    botMessageDiv.textContent = '';
    newHandBtn.disabled = false;
  } else if (data.to_act === "player") {
    enableActions(true);
  } else {
    enableActions(false);
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }
}

const newHandBtn = document.createElement('button');
newHandBtn.textContent = 'Nueva Mano';
newHandBtn.onclick = iniciarPartida;
document.body.appendChild(newHandBtn);

async function iniciarPartida() {
  newHandBtn.disabled = true;
  logContainer.innerHTML = '';

  const res = await fetch('/api/start_hand', {method: 'POST'});
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    newHandBtn.disabled = false;
    return;
  }

  gameState = data;
  renderCards();
  updateStatus();

  if (gameState.to_act === "player") {
    enableActions(true);
  } else {
    enableActions(false);
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }

  if (data.log) {
    for (const m of data.log) {
      log(m);
    }
    updatePlayerMessages(data.log);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  iniciarPartida();
});
