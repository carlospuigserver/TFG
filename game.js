// ----------------------------------------------------------
// game.js
// Lógica de la partida (cliente-side). Comunica con Flask
// ----------------------------------------------------------

// Generamos un session_id único para esta partida
const sessionId = crypto.randomUUID();

// Referencias globales a contenedores en el DOM
let potDisplay, playerChipsDisplay, botChipsDisplay;
let communityContainer, playerCardsContainer, botCardsContainer;
let actionsContainer, messageContainer;

/**
 * Inicia la partida: llama a /api/new_hand,  
 * ajusta el DOM y dibuja las cartas iniciales (hole cards del jugador
 * y cartas boca abajo para el bot).
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

      // 1) Referencias a elementos del DOM (para actualizar rápidamente)
      potDisplay = document.getElementById("pot");
      playerChipsDisplay = document.getElementById("playerChips");
      botChipsDisplay = document.getElementById("botChips");
      communityContainer = document.getElementById("communityCards");
      playerCardsContainer = document.getElementById("playerCards");
      botCardsContainer = document.getElementById("botCards");
      actionsContainer = document.getElementById("actionsContainer");
      messageContainer = document.getElementById("messageContainer");

      // 2) Actualizar pot y stacks
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);

      // 3) Mostrar hole cards del jugador (data.player_hole es array de strings, p.ej. ["AH", "9D"])
      mostrarHoleCards(data.player_hole);

      // 4) Mostrar las cartas boca abajo del bot (2 cartas con card_back.png)
      mostrarBotCardsBack();

      // 5) Habilitar los botones de acción (Fold / Call / Raise + input)
      habilitarBotonesDeAccion();

      // 6) Limpiar mensajes previos
      messageContainer.textContent = "";
    })
    .catch(err => {
      console.error("Error en new_hand:", err);
      alert("No se pudo conectar con el servidor.");
    });
}

/**
 * Muestra las hole cards del jugador.  
 * hole: ["AH", "9D"] etc.
 */
function mostrarHoleCards(hole) {
  // Limpiar contenedor
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
 * Dibuja dos cartas boca abajo para el bot (card_back.png)
 * al inicio de la mano.  
 * (Más tarde, en el showdown, las reemplazaremos por las cartas reales.)
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
 * Revela (muestra) las hole cards reales del bot reemplazando las
 * cartas boca abajo.  
 * recibe un array: ["KC", "2H"], etc.
 */
function mostrarBotHoleCards(botHole) {
  botCardsContainer.innerHTML = "";
  botHole.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `cards/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    botCardsContainer.appendChild(img);
  });
}

/**
 * Actualiza los displays de pot, fichas del jugador y del bot.
 */
function actualizarPotYStacks(pot, playerChips, botChips) {
  potDisplay.textContent = pot;
  playerChipsDisplay.textContent = playerChips;
  botChipsDisplay.textContent = botChips;
}

/**
 * Dibuja o actualiza las cartas comunitarias en la mesa.
 * community: [] (preflop), 3 (flop), 4 (flop+turn) o 5 (flop+turn+river)
 */
function pintarBoard(community) {
  communityContainer.innerHTML = "";
  community.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `cards/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    communityContainer.appendChild(img);
  });
}

/**
 * Crea y habilita los botones Fold, Call y Raise (con un input numérico).
 */
function habilitarBotonesDeAccion() {
  actionsContainer.innerHTML = "";

  // Fold
  const btnFold = document.createElement("button");
  btnFold.textContent = "Fold";
  btnFold.onclick = () => enviarAccionJugador("fold", null);
  actionsContainer.appendChild(btnFold);

  // Call
  const btnCall = document.createElement("button");
  btnCall.textContent = "Call";
  btnCall.onclick = () => enviarAccionJugador("call", null);
  actionsContainer.appendChild(btnCall);

  // Input para Raise
  const inputRaise = document.createElement("input");
  inputRaise.type = "number";
  inputRaise.id = "raiseInput";
  inputRaise.placeholder = "Monto";
  inputRaise.min = "1";
  actionsContainer.appendChild(inputRaise);

  // Raise
  const btnRaise = document.createElement("button");
  btnRaise.textContent = "Raise";
  btnRaise.onclick = () => {
    const valor = parseInt(document.getElementById("raiseInput").value, 10);
    if (!valor || valor < 1) {
      alert("Ingresa un monto válido (>= 1).");
      return;
    }
    enviarAccionJugador("raise", valor);
  };
  actionsContainer.appendChild(btnRaise);
}

/**
 * Envía la acción del jugador al servidor Flask y procesa la respuesta.
 * action: "fold" | "call" | "raise"
 * raiseAmount: número | null
 */
function enviarAccionJugador(action, raiseAmount) {
  // Limpiar cualquier mensaje previo
  messageContainer.textContent = "";

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

      // Si la mano terminó con el jugador fold o con all-in resultante
      if (data.result === "player_ended") {
        // Mostramos mensaje de “Ganaste” y revelamos cartas del bot si vienen
        messageContainer.textContent = "¡Ganas! El bot se retiró.";
        if (data.bot_hole) {
          mostrarBotHoleCards(data.bot_hole);
        }
        accionesFinalMano();
        return;
      }
      if (data.result === "bot_ended") {
        // El bot ganó (fold o all-in), revelamos cartas del bot y mensaje
        messageContainer.textContent = "El bot gana la mano.";
        if (data.bot_hole) {
          mostrarBotHoleCards(data.bot_hole);
        }
        actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);
        accionesFinalMano();
        return;
      }

      // ---------- Mano continúa ----------
      // 1) Actualizar pot y stacks
      actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);

      // 2) Pintar cartas comunitarias (si hay alguna nueva)
      if (data.community) {
        pintarBoard(data.community);
      }

      // 3) Mostrar acción del bot (p.ej. “CALL” o “RAISE”)
      let txt = `El bot hizo ${data.bot_action}`;
      if (data.bot_raise_amount !== null && data.bot_raise_amount !== undefined) {
        txt += ` de ${data.bot_raise_amount}`;
      }
      messageContainer.textContent = txt;
    })
    .catch(err => {
      console.error("Error en player_action:", err);
      alert("No se pudo conectar con el servidor.");
    });
}

/**
 * Deshabilita los botones de acción y muestra “Nueva mano”.
 */
function accionesFinalMano() {
  // Limpiar contenedor de acciones
  actionsContainer.innerHTML = "";

  // Botón para recargar la página y empezar una nueva mano
  const btnNueva = document.createElement("button");
  btnNueva.textContent = "Nueva mano";
  btnNueva.onclick = () => {
    window.location.reload();
  };
  actionsContainer.appendChild(btnNueva);
}
