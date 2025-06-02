// game.js

// Generamos un session_id único para esta partida
const sessionId = crypto.randomUUID();

// Cuando se cargue la página, atamos el botón “Partida” del menú
window.addEventListener("DOMContentLoaded", () => {
  const btnPartida = document.getElementById("btnPartida");
  btnPartida.addEventListener("click", iniciarPartida);
});

// Variables globales para mantener referencias al DOM durante la partida
let actionsContainer, communityContainer, playerCardsContainer;
let potDisplay, playerChipsDisplay, botChipsDisplay;
let messageContainer;

/**
 * Función que se ejecuta cuando el usuario pulsa “Partida” en el menú.
 * 1) Llama a POST /api/new_hand para iniciar la mano.
 * 2) Esconde el menú y despliega la interfaz de juego.
 * 3) Muestra las hole cards del jugador y actualiza pot/stacks.
 * 4) Crea botones de acción (Fold, Call, Raise + input).
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

    // 1) Ocultar el menú principal (div que contiene btnPartida, btnEstadistica)
    const menu = document.querySelector(".contenedor-botones");
    if (menu) menu.style.display = "none";

    // 2) Construir la interfaz de juego (divs para cartas, pot, stacks, mensajes)
    buildGameInterface();

    // 3) Mostrar hole cards del jugador
    mostrarHoleCards(data.player_hole);

    // 4) Actualizar pot y stacks
    actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);

    // 5) Habilitar botones de acción (incluye input para Raise)
    habilitarBotonesDeAccion();
  });
}

/**
 * Crea dinámicamente la estructura HTML para la mesa de poker:
 *  - Contenedores para community cards, player cards.
 *  - Displays para pot, player chips, bot chips.
 *  - Contenedor para botones de acción + input raise.
 *  - Contenedor para mensajes (ej. “El bot hizo CALL”, “Ganas la mano”).
 */
function buildGameInterface() {
  // Contenedor principal de la partida
  const gameContainer = document.createElement("div");
  gameContainer.id = "gameContainer";
  gameContainer.style.display = "flex";
  gameContainer.style.flexDirection = "column";
  gameContainer.style.alignItems = "center";
  gameContainer.style.gap = "1rem";
  document.body.appendChild(gameContainer);

  // Display de pot y stacks
  const statusBar = document.createElement("div");
  statusBar.id = "statusBar";
  statusBar.style.display = "flex";
  statusBar.style.justifyContent = "space-around";
  statusBar.style.width = "80%";
  statusBar.innerHTML = `
    <div>Pot: <span id="pot">0</span></div>
    <div>Tú: <span id="playerChips">0</span> fichas</div>
    <div>Bot: <span id="botChips">0</span> fichas</div>
  `;
  gameContainer.appendChild(statusBar);

  // Contenedor de community cards
  communityContainer = document.createElement("div");
  communityContainer.id = "communityCards";
  communityContainer.style.display = "flex";
  communityContainer.style.gap = "0.5rem";
  gameContainer.appendChild(communityContainer);

  // Contenedor de las hole cards del jugador
  playerCardsContainer = document.createElement("div");
  playerCardsContainer.id = "playerCards";
  playerCardsContainer.style.display = "flex";
  playerCardsContainer.style.gap = "0.5rem";
  gameContainer.appendChild(playerCardsContainer);

  // Contenedor de botones de acción + input raise
  actionsContainer = document.createElement("div");
  actionsContainer.id = "actionsContainer";
  actionsContainer.style.display = "flex";
  actionsContainer.style.alignItems = "center";
  actionsContainer.style.gap = "1rem";
  gameContainer.appendChild(actionsContainer);

  // Contenedor de mensajes (ej. acciones del bot, fin de mano, etc.)
  messageContainer = document.createElement("div");
  messageContainer.id = "messageContainer";
  messageContainer.style.marginTop = "1rem";
  messageContainer.style.fontSize = "1.2rem";
  messageContainer.style.fontWeight = "bold";
  gameContainer.appendChild(messageContainer);

  // Referencias a los displays para actualizaciones rápidas
  potDisplay = document.getElementById("pot");
  playerChipsDisplay = document.getElementById("playerChips");
  botChipsDisplay = document.getElementById("botChips");
}

/**
 * Muestra en pantalla las hole cards del jugador.
 * Recibe un array de strings, p.ej. ["AS","9D"].
 */
function mostrarHoleCards(hole) {
  // Limpiar cualquier carta previa
  playerCardsContainer.innerHTML = "";

  hole.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `/static/img/cartas/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    playerCardsContainer.appendChild(img);
  });
}

/**
 * Actualiza los displays de pot y stacks.
 */
function actualizarPotYStacks(pot, playerChips, botChips) {
  if (potDisplay) potDisplay.textContent = pot;
  if (playerChipsDisplay) playerChipsDisplay.textContent = playerChips;
  if (botChipsDisplay) botChipsDisplay.textContent = botChips;
}

/**
 * Dibuja las cartas comunitarias en función del array recibido.
 * community: puede ser [] (preflop), 3 cartas (flop), 4 (flop+turn), o 5 (flop+turn+river).
 * streetIndex: 0 (preflop), 1 (flop), 2 (turn), 3 (river).
 */
function pintarBoard(community, streetIndex) {
  // Limpiar antes de repintar
  communityContainer.innerHTML = "";

  community.forEach(cardCode => {
    const img = document.createElement("img");
    img.src = `/static/img/cartas/${cardCode}.png`;
    img.alt = cardCode;
    img.width = 80;
    img.height = 120;
    communityContainer.appendChild(img);
  });
}

/**
 * Muestra en pantalla la acción que ha realizado el bot.
 * botAction es algo como "CALL" o "RAISE_MEDIUM"; botRaiseAmount es null o número.
 */
function mostrarAccionBot(botAction, botRaiseAmount) {
  let txt = `El bot hizo ${botAction}`;
  if (botRaiseAmount !== null && botRaiseAmount !== undefined) {
    txt += ` de ${botRaiseAmount}`;
  }
  messageContainer.textContent = txt;
}

/**
 * Crea y habilita los botones Fold, Call y Raise con un input numérico para monto.
 */
function habilitarBotonesDeAccion() {
  actionsContainer.innerHTML = "";

  // Botón Fold
  const btnFold = document.createElement("button");
  btnFold.textContent = "Fold";
  btnFold.onclick = () => enviarAccionJugador("fold", null);
  btnFold.style.padding = "0.5rem 1rem";
  actionsContainer.appendChild(btnFold);

  // Botón Call
  const btnCall = document.createElement("button");
  btnCall.textContent = "Call";
  btnCall.onclick = () => enviarAccionJugador("call", null);
  btnCall.style.padding = "0.5rem 1rem";
  actionsContainer.appendChild(btnCall);

  // Input para Raise
  const inputRaise = document.createElement("input");
  inputRaise.type = "number";
  inputRaise.id = "raiseInput";
  inputRaise.placeholder = "Monto Raise";
  inputRaise.min = "1";
  inputRaise.style.width = "80px";
  inputRaise.style.padding = "0.3rem";
  actionsContainer.appendChild(inputRaise);

  // Botón Raise
  const btnRaise = document.createElement("button");
  btnRaise.textContent = "Raise";
  btnRaise.onclick = () => {
    const valor = parseInt(document.getElementById("raiseInput").value, 10);
    if (!valor || valor < 1) {
      alert("Ingresa un monto válido para Raise (>= 1).");
      return;
    }
    enviarAccionJugador("raise", valor);
  };
  btnRaise.style.padding = "0.5rem 1rem";
  actionsContainer.appendChild(btnRaise);
}

/**
 * Envía la acción del jugador al servidor y procesa la respuesta.
 * action: "fold"|"call"|"raise"; raiseAmount: número|null
 */
function enviarAccionJugador(action, raiseAmount) {
  // Limpiar mensaje previo
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

    // Si la respuesta incluye "result", significa que la mano terminó
    if (data.result === "player_ended") {
      mostrarMensajeFin("¡Ganas! El bot foldeó o pagaste su all-in.");
      return;
    }
    if (data.result === "bot_ended") {
      mostrarMensajeFin("El bot gana la mano.");
      return;
    }

    // Mano continúa: actualizamos estado
    // 1) Actualizar pot y stacks
    actualizarPotYStacks(data.pot, data.player_chips, data.bot_chips);

    // 2) Pintar board si hay cartas comunitarias nuevas
    pintarBoard(data.community, data.street_index);

    // 3) Mostrar acción del bot
    mostrarAccionBot(data.bot_action, data.bot_raise_amount);
  });
}

/**
 * Muestra un mensaje de fin de mano, deshabilita los botones y ofrece reiniciar mano.
 */
function mostrarMensajeFin(texto) {
  // Deshabilitar los botones de Fold/Call/Raise
  actionsContainer.innerHTML = "";

  // Mostrar mensaje final
  messageContainer.textContent = texto;

  // Botón "Nueva mano"
  const btnNuevaMano = document.createElement("button");
  btnNuevaMano.textContent = "Nueva mano";
  btnNuevaMano.style.marginTop = "1rem";
  btnNuevaMano.style.padding = "0.5rem 1rem";
  btnNuevaMano.onclick = () => {
    // Recargamos la página para empezar de nuevo
    window.location.reload();
  };
  actionsContainer.appendChild(btnNuevaMano);
}
