// ----------------------------------------------------------
// game.js
// Control de la partida en el cliente. Se comunica con Flask.
// ----------------------------------------------------------

// Generamos un session_id único para cada jugador
const sessionId = crypto.randomUUID();

// Referencias globales a los elementos del DOM
let potDisplay, playerChipsDisplay, botChipsDisplay;
let dealerDisplay, toActDisplay;
let communityContainer, playerCardsContainer, botCardsContainer;
let actionsContainer;
let botMessageContainer, playerMessageContainer;

/**
 * Inicia la partida: llama a /api/new_hand,  
 * configura el DOM y dibuja las cartas iniciales.
 */
function iniciarPartida() {
  fetch("/api/new_hand", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert("Error al iniciar la mano: " + data.error);
        return;
      }

      // 1) Obtenemos referencias a todos los elementos del DOM
      potDisplay = document.getElementById("pot");
      playerChipsDisplay = document.getElementById("playerChips");
      botChipsDisplay = document.getElementById("botChips");
      dealerDisplay = document.getElementById("dealerDisplay");
      toActDisplay = document.getElementById("toActDisplay");
      communityContainer = document.getElementById("communityCards");
      playerCardsContainer = document.getElementById("playerCards");
      botCardsContainer = document.getElementById("botCards");
      actionsContainer = document.getElementById("actionsContainer");
      botMessageContainer = document.getElementById("botMessage");
      playerMessageContainer = document.getElementById("playerMessage");

      // 2) Actualizamos pot, stacks, dealer y turno inicial
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);

      // 3) Pintamos las hole cards del jugador
      mostrarHoleCards(data.player_hole);

      // 4) Pintamos dos cartas boca abajo para el bot
      mostrarBotCardsBack();

      // 5) Limpiamos los mensajes (jugador y bot)
      botMessageContainer.textContent = "";
      playerMessageContainer.textContent = "";

      // 6) Habilitamos los botones de acción
      habilitarBotonesDeAccion();
    })
    .catch(err => {
      console.error("Error en new_hand:", err);
      alert("No se pudo conectar con el servidor.");
    });
}

/**
 * Dibuja las hole cards del jugador (p. ej. ["AH","9D"]).
 */
function mostrarHoleCards(hole) {
  playerCardsContainer.innerHTML = "";
  hole.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `cards/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    playerCardsContainer.appendChild(img);
  });
}

/**
 * Muestra dos cartas boca abajo (card_back.png) para el bot.
 */
function mostrarBotCardsBack() {
  botCardsContainer.innerHTML = "";
  for (let i = 0; i < 2; i++) {
    const img = document.createElement("img");
    img.src = "card_back.png";
    img.alt = "Bot Card Back";
    img.width = 80;
    img.height = 120;
    // Con CSS ya están rotadas 180° para apuntar hacia abajo
    botCardsContainer.appendChild(img);
  }
}

/**
 * Revela las hole cards reales del bot
 * (reemplaza las cartas “boca abajo” por las suyas).
 */
function mostrarBotHoleCards(botHole) {
  botCardsContainer.innerHTML = "";
  botHole.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `cards/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    // Queremos mostrarlas “derechas” (sin rotación), así que:
    img.style.transform = "none";
    botCardsContainer.appendChild(img);
  });
}

/**
 * Actualiza los displays de pot, fichas del jugador y fichas del bot.
 */
function actualizarPotYStacks(pot, playerChips, botChips) {
  potDisplay.textContent = pot;
  playerChipsDisplay.textContent = playerChips;
  botChipsDisplay.textContent = botChips;
}

/**
 * Transforma "player"/"bot" en “Tú” o “Bot” (para mostrarlo bonito).
 */
function formateaNombre(quien) {
  if (quien === "player") return "Tú";
  if (quien === "bot") return "Bot";
  return quien;
}

/**
 * Dibuja las cartas comunitarias en el centro de la mesa.  
 * community: array de códigos, p. ej. ["5H","TD","2C","JH"].
 */
function pintarBoard(community) {
  communityContainer.innerHTML = "";
  community.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `cards/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    img.style.transform = "none";
    communityContainer.appendChild(img);
  });
}

/**
 * Crea los botones Fold, Call, el input + botón Raise.
 */
function habilitarBotonesDeAccion() {
  actionsContainer.innerHTML = "";

  // --- Fold ---
  const btnFold = document.createElement("button");
  btnFold.textContent = "Fold";
  btnFold.onclick = () => {
    playerMessageContainer.textContent = "Tú te retiras (Fold).";
    enviarAccionJugador("fold", null);
  };
  actionsContainer.appendChild(btnFold);

  // --- Call ---
  const btnCall = document.createElement("button");
  btnCall.textContent = "Call";
  btnCall.onclick = () => {
    playerMessageContainer.textContent = "Tú haces Call.";
    enviarAccionJugador("call", null);
  };
  actionsContainer.appendChild(btnCall);

  // --- Input para Raise ---
  const inputRaise = document.createElement("input");
  inputRaise.type = "number";
  inputRaise.id = "raiseInput";
  inputRaise.placeholder = "Monto";
  inputRaise.min = "1";
  actionsContainer.appendChild(inputRaise);

  // --- Raise ---
  const btnRaise = document.createElement("button");
  btnRaise.textContent = "Raise";
  btnRaise.onclick = () => {
    const valor = parseInt(document.getElementById("raiseInput").value, 10);
    if (!valor || valor < 1) {
      alert("Ingresa un monto válido (>= 1).");
      return;
    }
    playerMessageContainer.textContent = `Tú haces Raise de ${valor}.`;
    enviarAccionJugador("raise", valor);
  };
  actionsContainer.appendChild(btnRaise);
}

/**
 * Envía la acción del jugador al servidor y procesa la respuesta.  
 * action: "fold" | "call" | "raise"  
 * raiseAmount: número (o null).
 */
function enviarAccionJugador(action, raiseAmount) {
  fetch("/api/player_action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      action: action,
      raise_amount: raiseAmount
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert("Error en player_action: " + data.error);
        return;
      }

      // ---------- Caso A: la mano terminó ----------
      if (data.result === "player_ended") {
        botMessageContainer.textContent = "El bot se retira. ¡Tú ganas!";
        if (data.bot_hole) {
          mostrarBotHoleCards(data.bot_hole);
        }
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }
      if (data.result === "bot_ended") {
        botMessageContainer.textContent = "El bot gana la mano.";
        if (data.bot_hole) {
          mostrarBotHoleCards(data.bot_hole);
        }
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }

      // ---------- Caso B: la mano continúa ----------
      // 1) Pintar comunidad si hay nuevas cartas
      if (data.community && data.community.length > 0) {
        pintarBoard(data.community);
      }

      // 2) Actualizar pot y stacks
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);

      // 3) Mostrar acción del bot
      let textoBot = `El bot hace ${data.bot_action}`;
      if (data.bot_raise_amount !== null && data.bot_raise_amount !== undefined) {
        textoBot += ` de ${data.bot_raise_amount}`;
      }
      botMessageContainer.textContent = textoBot;

      // 4) Actualizar “Dealer” y “Turno” (por si cambió en esta ronda)
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);
    })
    .catch(err => {
      console.error("Error en player_action:", err);
      alert("No se pudo conectar con el servidor.");
    });
}

/**
 * Cuando la mano termina, reemplazamos los botones por “Nueva mano”.
 */
function accionesFinalMano() {
  actionsContainer.innerHTML = "";

  const btnNueva = document.createElement("button");
  btnNueva.textContent = "Nueva mano";
  btnNueva.onclick = () => {
    window.location.reload();
  };
  actionsContainer.appendChild(btnNueva);

  // Deshabilitamos el input de Raise si existe
  const inputRaise = document.getElementById("raiseInput");
  if (inputRaise) inputRaise.disabled = true;
}
