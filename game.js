// ==========================================================
// VARIABLES GLOBALES Y REFERENCIAS A ELEMENTOS DEL DOM
// ==========================================================
const potSpan            = document.getElementById('pot');
const playerChipsSpan    = document.getElementById('playerChips');
const botChipsSpan       = document.getElementById('botChips');
const dealerSpan         = document.getElementById('dealerDisplay');
const toActSpan          = document.getElementById('toActDisplay');
const playerWinsSpan     = document.getElementById('playerWins');
const botWinsSpan        = document.getElementById('botWins');
const sbSpan             = document.getElementById('sbDisplay');
const bbSpan             = document.getElementById('bbDisplay');

const botCardsDiv        = document.getElementById('botCards');
const playerCardsDiv     = document.getElementById('playerCards');
const communityCardsDiv  = document.getElementById('communityCards');
const botMessageDiv      = document.getElementById('botMessage');
const showdownCenterDiv  = document.getElementById('showdownCenter');
const showdownDetailsDiv = document.getElementById('showdownDetails');
const playerMessageDiv   = document.getElementById('playerMessage');
const actionsContainer   = document.getElementById('actionsContainer');

const btnNuevaMano       = document.getElementById('btnNuevaMano');
const btnEstadisticas    = document.getElementById('btnEstadisticas');
const sideButtonsDiv     = document.getElementById('sideButtons');

let gameState = null;
let marcador = { player: 0, bot: 0 };
let manosJugadas = 0;

// ----------------------------------------------------------
function cardToImg(card) {
  if (card === "card_back") {
    return '<img src="card_back.png" alt="Carta Oculta" class="card">';
  }
  const filename = card.toLowerCase() + '.png';
  return `<img src="cards/${filename}" alt="${card}" class="card">`;
}

// ----------------------------------------------------------
function renderCards() {
  botCardsDiv.innerHTML       = gameState.bot_hole.map(c => cardToImg(c)).join('');
  playerCardsDiv.innerHTML    = gameState.player_hole.map(c => cardToImg(c)).join('');
  communityCardsDiv.innerHTML = gameState.community_cards.map(c => cardToImg(c)).join('');
}

// ----------------------------------------------------------
function updateStatus() {
  potSpan.textContent         = gameState.pot;
  playerChipsSpan.textContent = gameState.player_chips;
  botChipsSpan.textContent    = gameState.bot_chips;
  dealerSpan.textContent      = gameState.dealer;

  sbSpan.textContent          = gameState.sb || 10;
  bbSpan.textContent          = gameState.bb || 20;
}

// ----------------------------------------------------------
function updateBotMessage(logs) {
  const lastBotMsg = logs.slice().reverse()
    .find(m => m.toLowerCase().startsWith("bot")) || '';
  botMessageDiv.textContent = lastBotMsg;
}

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
    if (data.player_chips === 0) marcador.bot++;
    if (data.bot_chips === 0) marcador.player++;
    manosJugadas++;

    playerWinsSpan.textContent = marcador.player;
    botWinsSpan.textContent    = marcador.bot;

    sbSpan.textContent = data.sb || 10;
    bbSpan.textContent = data.bb || 20;

    if (manosJugadas % 4 === 0) {
      showdownCenterDiv.textContent = "🔺 Ciegas aumentadas";
    }

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

  if (data.to_act === "player") {
    const hayAccionBot = data.log.some(line => line.toLowerCase().startsWith("bot"));
    if (hayAccionBot) {
      const ultimaAccion = data.log.slice().reverse().find(line => line.toLowerCase().startsWith("bot"));
      botMessageDiv.textContent = ultimaAccion;
    }
    setTimeout(() => {
      enableActions(true);
    }, 300);
  } else {
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

  if (gameState.hand_ended) {
    if (gameState.player_chips === 0) marcador.bot++;
    if (gameState.bot_chips === 0) marcador.player++;
    manosJugadas++;

    playerWinsSpan.textContent = marcador.player;
    botWinsSpan.textContent    = marcador.bot;

    sbSpan.textContent = gameState.sb || 10;
    bbSpan.textContent = gameState.bb || 20;

    if (manosJugadas % 4 === 0) {
      showdownCenterDiv.textContent = "🔺 Ciegas aumentadas";
    }

    enableActions(false);
    updateBotMessage(gameState.log);
    playerMessageDiv.textContent = 'Mano terminada. Elige “Nueva Partida” o “Estadísticas”.';
    btnNuevaMano.disabled = false;
    btnEstadisticas.disabled = false;
    sideButtonsDiv.style.display = 'flex';
    return;
  }

  if (gameState.log) {
    updateBotMessage(gameState.log);
  }

  if (gameState.to_act === "player") {
    enableActions(true);
    playerMessageDiv.textContent = "Tu turno: elige acción.";
  } else {
    const hayAccionBot = gameState.log.some(line => line.toLowerCase().startsWith("bot"));
    if (hayAccionBot) {
      botMessageDiv.textContent = gameState.log.find(line => line.toLowerCase().startsWith("bot"));
      enableActions(true);
    } else {
      enableActions(false);
      botMessageDiv.textContent = 'Esperando acción del bot...';
      fetch('/api/player_action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actor: 'bot' })
    })
    .then(res => res.json())
    .then(data => {
      gameState = data;
      renderCards();
      updateStatus();
      if (data.log) updateBotMessage(data.log);
      if (data.hand_ended) {
        if (data.player_chips === 0) marcador.bot++;
        if (data.bot_chips === 0) marcador.player++;
        manosJugadas++;
        playerWinsSpan.textContent = marcador.player;
        botWinsSpan.textContent = marcador.bot;
        showdownCenterDiv.textContent = "Fin de la mano";
        enableActions(false);
        playerMessageDiv.textContent = 'Mano terminada.';
        btnNuevaMano.disabled = false;
        btnEstadisticas.disabled = false;
        sideButtonsDiv.style.display = 'flex';
      } else if (data.to_act === "player") {
        setTimeout(() => {
          enableActions(true);
        }, 300);
      }
    })
    .catch(err => {
      console.error("Error al solicitar acción del bot:", err);
    });
    }
  }

  console.log("to_act:", gameState.to_act);
  console.log("log:", gameState.log);
}
