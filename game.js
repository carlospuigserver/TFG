// ----------------------------------------------------------
// game.js (detecta CHECK, limpia mensajes y muestra dealer/turno reales)
// ----------------------------------------------------------

// Generamos un session_id único para cada jugador
const sessionId = crypto.randomUUID();

// Referencias globales a los elementos del DOM
let potDisplay, playerChipsDisplay, botChipsDisplay;
let dealerDisplay, toActDisplay;
let communityContainer, playerCardsContainer, botCardsContainer;
let actionsContainer;
let botMessageContainer, playerMessageContainer;
let logContainer;  // donde mostraremos la “consola de logs”


/**
 * Inicia la partida: llama a /api/new_hand,
 * configura el DOM y dibuja las cartas iniciales.
 */
function iniciarPartida() {
  logContainer = document.getElementById("logContainer");

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

      // 1) Referencias a todos los elementos del DOM
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

      // 2) Limpiar logs antiguos
      logContainer.innerHTML = "";

      // 3) Pintar logs iniciales
      data.logs.forEach(line => {
        const p = document.createElement("div");
        p.textContent = line;
        logContainer.appendChild(p);
      });
      logContainer.scrollTop = logContainer.scrollHeight;

      // 4) Actualizar pot, stacks, dealer y turno
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);

      // 5) Pintar tus hole cards
      mostrarHoleCards(data.player_hole);

      // 6) Pintar cartas boca abajo del bot
      mostrarBotCardsBack();

      // 7) Inicializar zonas de mensajes vacías
      botMessageContainer.textContent = "";
      playerMessageContainer.textContent = "";

      // 8) Habilitar botones para tu primera acción
      habilitarBotonesDeAccion();
    })
    .catch(err => {
      console.error("Error en new_hand:", err);
      alert("No se pudo conectar con el servidor.");
    });
}


/**
 * Dibuja tus hole cards (por ejemplo ["AH","9D"]).
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
 * Muestra dos cartas boca abajo para el bot.
 */
function mostrarBotCardsBack() {
  botCardsContainer.innerHTML = "";
  for (let i = 0; i < 2; i++) {
    const img = document.createElement("img");
    img.src = "card_back.png";
    img.alt = "Bot Card Back";
    img.width = 80;
    img.height = 120;
    botCardsContainer.appendChild(img);
  }
}


/**
 * Revela las hole cards reales del bot.
 */
function mostrarBotHoleCards(botHole) {
  botCardsContainer.innerHTML = "";
  botHole.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `cards/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    img.style.transform = "none";
    botCardsContainer.appendChild(img);
  });
}


/**
 * Actualiza pot y stacks en pantalla.
 */
function actualizarPotYStacks(pot, playerChips, botChips) {
  potDisplay.textContent = pot;
  playerChipsDisplay.textContent = playerChips;
  botChipsDisplay.textContent = botChips;
}


/**
 * Convierte "player"/"bot" en “Tú” o “Bot”.
 */
function formateaNombre(quien) {
  if (quien === "player") return "Tú";
  if (quien === "bot") return "Bot";
  return quien;
}


/**
 * Dibuja las cartas comunitarias en el centro.
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
    // 1) Muestro en tu zona que “Tú te retiras”
    playerMessageContainer.textContent = "Tú te retiras (Fold).";
    // 2) Envío acción
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
  // Deshabilito de inmediato los botones para evitar dobles clics
  actionsContainer.querySelectorAll("button, input").forEach(el => (el.disabled = true));

  // Limpio de antemano ambos mensajes para que no se solapen
  playerMessageContainer.textContent = "";
  botMessageContainer.textContent = "";

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

      // 0) Pinto todos los logs que vienen (incluyen “Bot hace CHECK.”, “Bot hace CALL…”, etc.)
      if (data.logs && Array.isArray(data.logs)) {
        data.logs.forEach(line => {
          const p = document.createElement("div");
          p.textContent = line;
          logContainer.appendChild(p);
        });
        logContainer.scrollTop = logContainer.scrollHeight;
      }

      // 1) Caso “player_ended” (tú te retiras o all‐in terminó la mano)
      if (data.result === "player_ended") {
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

      // 2) Caso “bot_folded” (el bot se retira)
      if (data.result === "bot_folded") {
        botMessageContainer.textContent = "El bot se retira. ¡Tú ganas!";
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }

      // 3) Caso “bot_ended” (el bot gana por all‐in o porque tú te retiraste)
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

      // 4) Caso “new_street” (avanzamos de calle sin que el bot actúe)
      if (data.result === "new_street") {
        // a) Pinto la nueva comunidad
        if (data.community && data.community.length > 0) {
          pintarBoard(data.community);
        }
        // b) Actualizo pot y stacks
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        // c) Limpio ambos mensajes (jugador y bot)
        playerMessageContainer.textContent = "";
        botMessageContainer.textContent = "";
        // d) Actualizo Dealer y Turno
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = formateaNombre(data.to_act);
        // e) Reactivo botones para la nueva ronda
        habilitarBotonesDeAccion();
        return;
      }

      // 5) Caso “showdown” (final de mano)
      if (data.result === "showdown") {
        // a) Pinto toda la comunidad (si no estaba ya pintada)
        if (data.community && data.community.length > 0) {
          pintarBoard(data.community);
        }
        // b) Revelo cartas del bot
        if (data.bot_hole) {
          mostrarBotHoleCards(data.bot_hole);
        }
        // c) Actualizo pot y stacks finales
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }

      // 6) Caso “la mano continúa” (el bot actuó y no terminó ni igualó al mismo tiempo)
      //    a) Pinto comunidad parcial si hubo nueva carta
      if (data.community && data.community.length > 0) {
        pintarBoard(data.community);
      }
      //    b) Actualizo pot y stacks
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);

      //    c) Busco en los logs la última línea del bot para mostrarla
      let botLine = "";
      if (data.logs && data.logs.length > 0) {
        for (let i = data.logs.length - 1; i >= 0; i--) {
          const txt = data.logs[i];
          if (
            txt.startsWith("Bot hace CHECK") ||
            txt.startsWith("Bot hace CALL") ||
            txt.startsWith("Bot hace RAISE") ||
            txt.startsWith("Bot se retira")
          ) {
            botLine = txt;
            break;
          }
        }
      }
      if (botLine) {
        botMessageContainer.textContent = botLine;
      }

      //    d) Actualizo Dealer y Turno
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);

      //    e) Reactivo botones para que el jugador responda (si no es showdown)
      if (data.street_index < 4) {
        habilitarBotonesDeAccion();
      } else {
        accionesFinalMano();
      }
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

  const inputRaise = document.getElementById("raiseInput");
  if (inputRaise) inputRaise.disabled = true;
}


// Al cargar la página, vinculamos iniciarPartida() al event listener
window.addEventListener("DOMContentLoaded", () => {
  iniciarPartida();
});
