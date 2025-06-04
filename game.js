// ==========================================================
// VARIABLES GLOBALES Y REFERENCIAS A ELEMENTOS DEL DOM
// ==========================================================
const potSpan            = document.getElementById('pot');
const playerChipsSpan    = document.getElementById('playerChips');
const botChipsSpan       = document.getElementById('botChips');
const dealerSpan         = document.getElementById('dealerDisplay');
const toActSpan          = document.getElementById('toActDisplay');

const botCardsDiv        = document.getElementById('botCards');
const playerCardsDiv     = document.getElementById('playerCards');
const communityCardsDiv  = document.getElementById('communityCards');
const botMessageDiv      = document.getElementById('botMessage');
const showdownCenterDiv  = document.getElementById('showdownCenter');
const showdownDetailsDiv = document.getElementById('showdownDetails');
const playerMessageDiv   = document.getElementById('playerMessage');
const actionsContainer   = document.getElementById('actionsContainer');
const logContainer       = document.getElementById('logContainer');

let gameState = null;

// Botón “Nueva Mano”
const newHandBtn = document.createElement('button');
newHandBtn.textContent = 'Nueva Mano';
newHandBtn.style.position = 'absolute';
newHandBtn.style.top = '5%';
newHandBtn.style.right = '5%';
newHandBtn.style.padding = '0.5rem 1rem';
newHandBtn.style.background = '#006600';
newHandBtn.style.color = '#fff';
newHandBtn.style.border = 'none';
newHandBtn.style.borderRadius = '6px';
newHandBtn.style.cursor = 'pointer';
newHandBtn.style.zIndex = '3';
newHandBtn.onclick = iniciarPartida;
document.body.appendChild(newHandBtn);

// ==========================================================
// FUNCIÓN AUXILIAR PARA LOG EN PANTALLA
// ==========================================================
function log(msg) {
  const p = document.createElement('p');
  p.textContent = msg;
  logContainer.appendChild(p);
  logContainer.scrollTop = logContainer.scrollHeight;
}

// ==========================================================
// CONVIERTE UN CÓDIGO DE CARTA (p.ej. "Ac", "Jh", etc.) EN <img>
// ==========================================================
function cardToImg(card) {
  if (card === "card_back") {
    return '<img src="card_back.png" alt="Carta Oculta" class="card">';
  }
  const filename = card.toLowerCase() + '.png';
  return `<img src="cards/${filename}" alt="${card}" class="card">`;
}

// ==========================================================
// PINTA LAS CARTAS EN PANTALLA (bot, jugador, comunitarias)
// ==========================================================
function renderCards() {
  botCardsDiv.innerHTML       = gameState.bot_hole.map(c => cardToImg(c)).join('');
  playerCardsDiv.innerHTML    = gameState.player_hole.map(c => cardToImg(c)).join('');
  communityCardsDiv.innerHTML = gameState.community_cards.map(c => cardToImg(c)).join('');
}

// ==========================================================
// ACTUALIZA LA BARRA DE ESTADO (pot, stacks, dealer, turno)
// ==========================================================
function updateStatus() {
  potSpan.textContent         = gameState.pot;
  playerChipsSpan.textContent = gameState.player_chips;
  botChipsSpan.textContent    = gameState.bot_chips;
  dealerSpan.textContent      = gameState.dealer;
  toActSpan.textContent       = gameState.to_act || '–';
}

// ==========================================================
// LIMPIA ÚNICAMENTE: acciones del jugador + mensaje del jugador.
// NO BORRA el mensaje del bot ni el showdown.
// ==========================================================
function clearPlayerZone() {
  actionsContainer.innerHTML = '';
  playerMessageDiv.textContent = '';
}

// ==========================================================
// FILTRA ÚLTIMOS MENSAJES (para mostrarlos junto a cada “jugador”)
//   - lastBotMsg: la última línea que empiece por “bot”
// ==========================================================
function updatePlayerMessages(logs) {
  const lastBotMsg = logs.slice().reverse()
    .find(m => m.toLowerCase().startsWith("bot")) || '';
  botMessageDiv.textContent = lastBotMsg;
}

// ==========================================================
// HABILITAR/DESHABILITAR BOTONES DE ACCIÓN DEL JUGADOR
//  - Si enable = true: pinta “Tu turno: elige acción.” Y genera botones.
//  - Si enable = false: borra botones y limpia mensaje del jugador.
// ==========================================================
function enableActions(enable) {
  clearPlayerZone();

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

// ==========================================================
// ENVIAR ACCIÓN DEL JUGADOR AL BACKEND
//  - action: 'fold', 'call' o 'raise'
//  - raise_amount: número (solo si action==='raise')
//  - Procesa logs y showdown
// ==========================================================
async function sendPlayerAction(action, raise_amount = null) {
  // 1) Log interno
  log(`Jugador: ${action}${raise_amount ? ' ' + raise_amount : ''}`);

  // 2) Petición al servidor
  const res = await fetch('/api/player_action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ action, raise_amount })
  });
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    return;
  }

  // 3) Actualizamos estado local y pintamos cartas/estatus
  gameState = data;
  renderCards();
  updateStatus();

  // 4) Procesamos logs: pintamos en consola y actualizamos mensaje del bot
  if (data.log) {
    for (const m of data.log) {
      log(m);
    }
    updatePlayerMessages(data.log);
  }

  // 5) Si la mano terminó (hand_ended = true), mostramos showdown
  if (data.hand_ended) {
    // 5.1) "Showdown!"
    const showdownLine = data.log.find(m =>
      m.toLowerCase().startsWith("showdown")
    ) || "";

    // 5.2) Frase de ganador: jugador, bot o empate (insensible a mayúsculas)
    const winnerLine = data.log.find(m => {
      const low = m.toLowerCase();
      return low.startsWith("¡ganas") ||
             low.startsWith("el bot gana") ||
             low.includes("empate");
    }) || "";

    // 5.3) "Tu mejor jugada: …"
    const tuMejorLine  = data.log.find(m =>
      m.toLowerCase().startsWith("tu mejor jugada")
    ) || "";

    // 5.4) "Mejor jugada del bot: …"
    const botMejorLine = data.log.find(m =>
      m.toLowerCase().startsWith("mejor jugada del bot")
    ) || "";

    // 5.5) Centro: solo “Showdown!”
    showdownCenterDiv.textContent = showdownLine;

    // 5.6) Derecha: tres líneas (ganador, tu mano, mano bot)
    const detalles = [winnerLine, tuMejorLine, botMejorLine]
      .filter(line => line)         // sólo incluimos las que existan
      .join("\n");
    showdownDetailsDiv.textContent = detalles;

    // 5.7) Limpiamos posible “Esperando acción del bot…”
    botMessageDiv.textContent = "";

    log('Mano terminada.');
    enableActions(false);
    playerMessageDiv.textContent = 'Mano terminada. Pulsa "Nueva Mano" para continuar.';
    newHandBtn.disabled = false;
    return;
  }

  // 6) Si sigue la mano y ahora es turno del jugador:
  if (data.to_act === "player") {
    setTimeout(() => {
      enableActions(true);
    }, 2000);
  }
  // 7) Si ahora toca al bot:
  else {
    enableActions(false);
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }
}

// ==========================================================
// INICIAR UNA NUEVA MANO
//  - Borra logs, showdown y pide /api/start_hand
// ==========================================================
async function iniciarPartida() {
  newHandBtn.disabled = true;
  logContainer.innerHTML         = '';
  showdownCenterDiv.textContent  = '';
  showdownDetailsDiv.textContent = '';
  botMessageDiv.textContent      = '';
  playerMessageDiv.textContent   = '';
  actionsContainer.innerHTML     = '';

  const res = await fetch('/api/start_hand', { method: 'POST' });
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    newHandBtn.disabled = false;
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

  if (gameState.to_act === "player") {
    enableActions(true);
  } else {
    enableActions(false);
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }
}

// ==========================================================
// AL CARGAR LA PÁGINA, ARRANCAMOS UNA MANO AUTOMÁTICAMENTE
// ==========================================================
document.addEventListener('DOMContentLoaded', () => {
  iniciarPartida();
});
