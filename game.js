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
  // 1) Mostrar la acción del jugador
  playerMessageDiv.textContent = `Jugador: ${action}${raise_amount ? ' ' + raise_amount : ''}`;

  // 2) Llamada al servidor
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

  // 3) Actualizamos estado en cliente
  gameState = data;
  renderCards();
  updateStatus();

  // 4) Actualizamos mensaje del bot
  if (data.log) {
    updateBotMessage(data.log);
  }

  // 5) Si la mano terminó (hand_ended = true), mostramos showdown y ganador/fold
  if (data.hand_ended) {
    // 5.1) Intentar buscar “Showdown!” en los logs
    const showdownLine = data.log.find(m =>
      m.toLowerCase().startsWith("showdown")
    ) || "";

    // 5.2) Línea con ganador: “¡Ganas…” o “El bot gana…” o “Empate…”
    const winnerLine = data.log.find(m => {
      const low = m.toLowerCase();
      return low.startsWith("¡ganas") ||
             low.startsWith("el bot gana") ||
             low.includes("empate");
    }) || "";

    // 5.3) “Tu mejor jugada: …”
    const tuMejorLine  = data.log.find(m =>
      m.toLowerCase().startsWith("tu mejor jugada")
    ) || "";

    // 5.4) “Mejor jugada del bot: …”
    const botMejorLine = data.log.find(m =>
      m.toLowerCase().startsWith("mejor jugada del bot")
    ) || "";

    // 5.5) Mostrar “Showdown!” en el centro (si existe)
    showdownCenterDiv.textContent = showdownLine;

    // 5.6) Mostrar detalles: ganador, tu mano y mano del bot
    const detalles = [winnerLine, tuMejorLine, botMejorLine]
      .filter(line => line)
      .join("\n");
    showdownDetailsDiv.textContent = detalles;

    // 5.7) Deshabilitar botones de acción y habilitar “Nueva Partida” / “Estadísticas”
    enableActions(false);
    playerMessageDiv.textContent = 'Mano terminada. Elige “Nueva Partida” o “Estadísticas”.';

    // Habilitar y mostrar los botones estáticos
    btnNuevaMano.disabled    = false;
    btnEstadisticas.disabled = false;
    sideButtonsDiv.style.display = 'flex';

    return;
  }

  // 6) Si la mano continúa y ahora es el turno del jugador:
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

// ----------------------------------------------------------
// Iniciar una nueva mano
// ----------------------------------------------------------
async function iniciarPartida() {
  // Ocultar y deshabilitar los botones estáticos al empezar:
  btnNuevaMano.disabled    = true;
  btnEstadisticas.disabled = true;
  sideButtonsDiv.style.display = 'none';

  // Limpiar mensajes y contenedores
  showdownCenterDiv.textContent  = '';
  showdownDetailsDiv.textContent = '';
  botMessageDiv.textContent      = '';
  playerMessageDiv.textContent   = '';
  actionsContainer.innerHTML     = '';

  // 1) Llamada al endpoint de Flask para iniciar mano
  const res  = await fetch('/api/start_hand', { method: 'POST' });
  const data = await res.json();

  if (data.error) {
    alert(data.error);
    // Si hay error, volvemos a habilitar el botón “Nueva Partida”
    btnNuevaMano.disabled = false;
    return;
  }

  // 2) Actualizar estado del juego
  gameState = data;
  renderCards();
  updateStatus();

  // 3) Mostrar último mensaje del bot (si existe)
  if (data.log) {
    updateBotMessage(data.log);
  }

  // 4) Si le toca al jugador, habilitar botones de acción; sino, esperar al bot
  if (gameState.to_act === "player") {
    enableActions(true);
  } else {
    enableActions(false);
    botMessageDiv.textContent = 'Esperando acción del bot...';
  }
}
