// ----------------------------------------------------------
// game.js (con actualizaciones para CHECK y limpieza de mensajes)
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

      // 2) Pongo los logs iniciales
      logContainer.innerHTML = "";
      data.logs.forEach(line => {
        const p = document.createElement("div");
        p.textContent = line;
        logContainer.appendChild(p);
      });

      // 3) Actualizo pot, stacks, dealer y turno
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);

      // 4) Pinto tus hole cards
      mostrarHoleCards(data.player_hole);

      // 5) Pinto las cartas boca abajo del bot
      mostrarBotCardsBack();

      // 6) Inicializo las zonas de mensajes vacías
      botMessageContainer.textContent = "";
      playerMessageContainer.textContent = "";

      // 7) Habilito los botones para que puedas actuar
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

      // 0) Actualizo los logs en pantalla
      if (data.logs && Array.isArray(data.logs)) {
        data.logs.forEach(line => {
          const p = document.createElement("div");
          p.textContent = line;
          logContainer.appendChild(p);
        });
        logContainer.scrollTop = logContainer.scrollHeight;
      }

      // 1) Caso “player_ended” (tú te retiras o all-in terminó la mano)
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
        // No revelo cartas del bot
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = "–";
        accionesFinalMano();
        return;
      }

      // 3) Caso “bot_ended” (el bot gana por all-in o porque tú te retiraste)
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

      // 4) Caso “new_street” (la apuesta se igualó y pasó a flop/turn/river sin que el bot actuara)
      if (data.result === "new_street") {
        // a) Pinto la nueva comunidad
        if (data.community && data.community.length > 0) {
          pintarBoard(data.community);
        }
        // b) Actualizo pot y stacks
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        // c) Limpio mensaje previo del bot y del jugador
        botMessageContainer.textContent = "";
        playerMessageContainer.textContent = "";
        // d) Actualizo Dealer y Turno
        dealerDisplay.textContent = formateaNombre(data.dealer);
        toActDisplay.textContent = formateaNombre(data.to_act);
        // e) Reactivo botones para que el jugador actúe en la nueva ronda
        habilitarBotonesDeAccion();
        return;
      }

      // 5) Caso “showdown” (llegamos al final y mostramos showdown)
      if (data.result === "showdown") {
        // a) Pinto flop/turn/river completo
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

      // 6) Caso “la mano continúa” (el bot sí actuó, pero no igualó apuestas ni terminó)
      //    a) Pinto comunidad parcial si la hubo (por si abrió flop/turn/river antes)
      if (data.community && data.community.length > 0) {
        pintarBoard(data.community);
      }
      //    b) Actualizo pot y stacks
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
      //    c) Limpio el mensaje del jugador (aparece solo durante tu turno)
      playerMessageContainer.textContent = "";
      //    d) Muestro la acción del bot en su zona
      let textoBot = `El bot hace ${data.bot_action}`;
      //    e) Si el bot hizo “RAISE”, agrego “de X”
      if (data.bot_raise_amount !== null && data.bot_raise_amount !== undefined) {
        textoBot += ` de ${data.bot_raise_amount}`;
      }
      botMessageContainer.textContent = textoBot;
      //    f) Actualizo Dealer y Turno
      dealerDisplay.textContent = formateaNombre(data.dealer);
      toActDisplay.textContent = formateaNombre(data.to_act);
      //    g) Reactivo botones para que el jugador vuelva a actuar (si no es showdown)
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
