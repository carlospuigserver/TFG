// game.js
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

// Referencias a los botones estáticos
const btnNuevaMano       = document.getElementById('btnNuevaMano');
const btnEstadisticas    = document.getElementById('btnEstadisticas');
const sideButtonsDiv     = document.getElementById('sideButtons');

let gameState = null;

// ----------------------------------------------------------
// Convertir un código de carta (p.ej. "Ac", "Jh", etc.) EN <img>
// ----------------------------------------------------------
function cardToImg(card) {
  if (card === "card_back") {
    return '<img src="card_back.png" alt="Carta Oculta" class="card">';
  }
  const filename = card.toLowerCase() + '.png';
  return `<img src="cards/${filename}" alt="${card}" class="card">`;
}

// ----------------------------------------------------------
// Pinta las cartas en pantalla (bot, jugador, comunitarias)
// ----------------------------------------------------------
function renderCards() {
  botCardsDiv.innerHTML       = gameState.bot_hole.map(c => cardToImg(c)).join('');
  playerCardsDiv.innerHTML    = gameState.player_hole.map(c => cardToImg(c)).join('');
  communityCardsDiv.innerHTML = gameState.community_cards.map(c => cardToImg(c)).join('');
}

// ----------------------------------------------------------
// Actualiza la barra de estado (pot, stacks, dealer, turno)
// ----------------------------------------------------------
function updateStatus() {
  potSpan.textContent         = gameState.pot;
  playerChipsSpan.textContent = gameState.player_chips;
  botChipsSpan.textContent    = gameState.bot_chips;
  dealerSpan.textContent      = gameState.dealer;
}

// ----------------------------------------------------------
// Mostrar la última acción relevante del bot en pantalla
// (extraída de los logs que devuelve el servidor).
// ----------------------------------------------------------
function updateBotMessage(logs) {
  const lastBotMsg = logs.slice().reverse()
    .find(m => m.toLowerCase().startsWith("bot")) || '';
  botMessageDiv.textContent = lastBotMsg;
}

// ----------------------------------------------------------
// Habilitar/Deshabilitar botones de acción del jugador
// ----------------------------------------------------------
function enableActions(enable) {
  actionsContainer.innerHTML  = '';
  playerMessageDiv.textContent = '';

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

// ----------------------------------------------------------
// Enviar acción del jugador al backend
// ----------------------------------------------------------
async function sendPlayerAction(action, raise_amount = null) {
  playerMessageDiv.textContent = `Jugador: ${action}${raise_amount ? ' ' + raise_amount : ''}`;

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

  gameState = data;
  renderCards();
  updateStatus();

  if (data.log) {
    updateBotMessage(data.log);
  }

  if (data.hand_ended) {
    const showdownLine = data.log.find(m =>
      m.toLowerCase().startsWith("showdown")
    ) || "";

    const winnerLine = data.log.find(m => {
      const low = m.toLowerCase();
      return low.startsWith("¡ganas") ||
             low.startsWith("el bot gana") ||
             low.includes("empate");
    }) || "";

    const tuMejorLine  = data.log.find(m =>
      m.toLowerCase().startsWith("tu mejor jugada")
    ) || "";

    const botMejorLine = data.log.find(m =>
      m.toLowerCase().startsWith("mejor jugada del bot")
    ) || "";

    showdownCenterDiv.textContent = showdownLine;

    const detalles = [winnerLine, tuMejorLine, botMejorLine]
      .filter(line => line)
      .join("\n");
    showdownDetailsDiv.textContent = detalles;

    enableActions(false);
    playerMessageDiv.textContent = 'Mano terminada. Elige “Nueva Partida” o “Estadísticas”.';
    btnNuevaMano.disabled = false;
    btnEstadisticas.disabled = false;
    sideButtonsDiv.style.display = 'flex';
    return;
  }

  // 6) Si ahora toca al jugador:
if (data.to_act === "player") {
  const hayAccionBot = data.log.some(line => line.toLowerCase().startsWith("bot"));
  if (hayAccionBot) {
    const ultimaAccion = data.log.slice().reverse().find(line => line.toLowerCase().startsWith("bot"));
    botMessageDiv.textContent = ultimaAccion;
  }
  setTimeout(() => {
    enableActions(true);
  }, 300);
}

// 7) Si ahora toca al bot:
else {
  const hayAccionBot = data.log.some(line => line.toLowerCase().startsWith("bot"));
  if (hayAccionBot) {
    const ultimaAccion = data.log.slice().reverse().find(line => line.toLowerCase().startsWith("bot"));
    botMessageDiv.textContent = ultimaAccion;
  } else {
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }
  enableActions(false);
}


}

// ----------------------------------------------------------
// Iniciar una nueva mano
// ----------------------------------------------------------
async function iniciarPartida() {
  btnNuevaMano.disabled    = true;
  btnEstadisticas.disabled = true;
  sideButtonsDiv.style.display = 'none';

  showdownCenterDiv.textContent  = '';
  showdownDetailsDiv.textContent = '';
  botMessageDiv.textContent      = '';
  playerMessageDiv.textContent   = '';
  actionsContainer.innerHTML     = '';

  const res  = await fetch('/api/start_hand', { method: 'POST' });
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    btnNuevaMano.disabled = false;
    return;
  }

  gameState = data;
  renderCards();
  updateStatus();

  // ✅ NUEVO BLOQUE FINAL ROBUSTO
if (gameState.hand_ended) {
  enableActions(false);
  updateBotMessage(gameState.log);
  playerMessageDiv.textContent = 'Mano terminada. Elige “Nueva Partida” o “Estadísticas”.';
  btnNuevaMano.disabled = false;
  btnEstadisticas.disabled = false;
  sideButtonsDiv.style.display = 'flex';
  return;
}

// ✅ Mostrar acción del bot si ya actuó
if (gameState.log) {
  updateBotMessage(gameState.log);
}

// ✅ Decidir turno realista
if (gameState.to_act === "player") {
  enableActions(true);
  playerMessageDiv.textContent = "Tu turno: elige acción.";
} else {
  // 🧠 Si ya hay acción del bot en el log, no mostramos "esperando"
  const hayAccionBot = gameState.log.some(line => line.toLowerCase().startsWith("bot"));
  if (hayAccionBot) {
    botMessageDiv.textContent = gameState.log.find(line => line.toLowerCase().startsWith("bot"));
    enableActions(true);  // Porque es el turno del jugador después de la acción del bot
  } else {
    enableActions(false);
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }
}


  // 💡 Consola útil para debug
  console.log("to_act:", gameState.to_act);
  console.log("log:", gameState.log);
}
