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
let logContainer;  // donde mostraremos la “consola de logs”

/**
 * Inicia la partida: llama a /api/new_hand,
 * configura el DOM y dibuja las cartas iniciales.
 */
function iniciarPartida() {
  // Obtenemos referencia a <div id="logContainer">
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

      // 2) VOLCAMOS los “logs” que vino en data.logs
      logContainer.innerHTML = "";
      data.logs.forEach(line => {
        const p = document.createElement("div");
        p.textContent = line;
        logContainer.appendChild(p);
      });

      // 3) Actualizamos pot, stacks, dealer y turno inicial
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);

      // 4) Pintamos las hole cards del jugador
      mostrarHoleCards(data.player_hole);

      // 5) Pintamos dos cartas boca abajo para el bot
      mostrarBotCardsBack();

      // 6) Limpiamos los mensajes (jugador y bot)
      botMessageContainer.textContent = "";
      playerMessageContainer.textContent = "";

      // 7) Habilitamos los botones de acción
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
  // Deshabilitamos botones para evitar clicks múltiples
  actionsContainer.querySelectorAll("button, input").forEach(el => (el.disabled = true));

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

      // 0) Actualizamos el “consola de logs”
      if (data.logs && Array.isArray(data.logs)) {
        data.logs.forEach(line => {
          const p = document.createElement("div");
          p.textContent = line;
          logContainer.appendChild(p);
        });
        logContainer.scrollTop = logContainer.scrollHeight;
      }

      // 1) Caso A: la mano terminó por fold o all-in (player_ended)
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

      // 2) Caso B: el bot se retira (bot_folded)
      if (data.result === "bot_folded") {
        botMessageContainer.textContent = "El bot se retira. ¡Tú ganas!";
        // No revelamos cartas del bot
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }

      // 3) Caso C: el bot gana direct (bot_ended)
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

      // 4) Caso D: se completó una ronda y avanzamos de calle sin que haya actuado el bot (new_street)
      if (data.result === "new_street") {
        // a) Pintar comunidad
        if (data.community && data.community.length > 0) {
          pintarBoard(data.community);
        }
        // b) Actualizar pot y stacks
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        // c) Limpiar mensajes previos de bot
        botMessageContainer.textContent = "";
        // d) Actualizar “Dealer” y “Turno”
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = formateaNombre(data.to_act);
        // e) Reactivar botones para la nueva ronda
        habilitarBotonesDeAccion();
        return;
      }

      // 5) Caso E: showdown tras igualar river o all-in (showdown)
      if (data.result === "showdown") {
        // a) Mostrar flop/turn/river completo si hace falta
        if (data.community && data.community.length > 0) {
          pintarBoard(data.community);
        }
        // b) Revelar bot hole cards
        if (data.bot_hole) {
          mostrarBotHoleCards(data.bot_hole);
        }
        // c) Actualizar pot y stacks finales
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }

      // 6) Caso F: la mano continúa (ambos han actuado pero no igualaron aún)
      //    a) Pintar comunidad parcial si llegó una nueva calle (en este escenario, el bot actuó en la misma calle)
      if (data.community && data.community.length > 0) {
        pintarBoard(data.community);
      }
      //    b) Actualizar pot y stacks
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
      //    c) Mostrar acción del bot
      let textoBot = `El bot hace ${data.bot_action}`;
      if (data.bot_raise_amount !== null && data.bot_raise_amount !== undefined) {
        textoBot += ` de ${data.bot_raise_amount}`;
      }
      botMessageContainer.textContent = textoBot;
      //    d) Actualizar “Dealer” y “Turno”
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);
      //    e) Reactivar botones para que el jugador siga (si no es showdown)
      if (data.street_index < 4) {
        habilitarBotonesDeAccion();
      } else {
        // Si llegamos por error a street_index 4 sin “showdown” explícito, forzamos final
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

  // Desactivar input de raise si existiera
  const inputRaise = document.getElementById("raiseInput");
  if (inputRaise) inputRaise.disabled = true;
}

// Al cargar la página, vinculamos iniciarPartida() al event listener
window.addEventListener("DOMContentLoaded", () => {
  iniciarPartida();
});
