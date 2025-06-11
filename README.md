# ANEXO – CÓDIGO FUENTE Y GUÍA DE DESPLIEGUE DEL MODELO
Este anexo tiene como finalidad servir de guía práctica y técnica para la ejecución del modelo desarrollado en el presente Trabajo de Fin de Grado, describiendo los pasos necesarios para su correcto despliegue, así como una breve descripción funcional de cada uno de los módulos que lo componen.
## 1. Acceso al Repositorio
El código completo se encuentra disponible en el siguiente repositorio de GitHub:
 http://enlacegithubrepositorio-tfg
 IMPORTANTE: Es imprescindible acceder a la rama ‘respaldo-entreno-nuevo’, ya que contiene la versión final del modelo funcional y validado. El uso de otra rama podría provocar fallos de ejecución o errores lógicos, ya que no implementan el estado definitivo del sistema.
## 2. Clonado y Preparación del Entorno
Para ejecutar el sistema, se recomienda utilizar Visual Studio Code como entorno de desarrollo.
Una vez clonado el repositorio, localice el archivo requirements.txt y ejecute en la terminal el siguiente comando:
pip install-r requirements.txt
Esto instalará todas las dependencias necesarias. Las principales librerías utilizadas son:
•	Flask – para el despliegue del entorno web interactivo.
•	scikit-learn – para la abstracción de estados mediante clustering KMeans.
•	matplotlib y pandas – para visualización y análisis de métricas de entrenamiento.
•	treys – librería especializada en evaluación de manos de póker.
•	joblib – para la serialización de modelos y estrategias.3. Ejecución del Modelo
### 2.1 Modo Terminal
Para jugar una partida simulada directamente desde la terminal, basta con ejecutar el siguiente script:
python practica.py

Este módulo inicia una partida entre el jugador humano (por consola) y el agente CFR entrenado.


### 2.2 Modo Web (Interfaz Gráfica Flask)
El modo principal y recomendado de uso es a través de la interfaz web. Para ello:
1.	Ejecutar el servidor Flask:
python app.py

2.	Acceder en el navegador a la dirección http://127.0.0.1:5000/ (la URL aparecerá en la terminal al iniciar el servidor).
Esto abrirá la interfaz gráfica del juego, donde el usuario podrá competir mano a mano contra el agente entrenado, visualizar las jugadas y recibir estadísticas y recomendaciones estratégicas al finalizar cada mano.

### 3. Entrenamiento y Evaluación del Modelo
Si se desea reentrenar el agente desde cero, se puede ejecutar el módulo:
python entrenamiento_completo.py


Este proceso genera dos archivos clave:
cfr_entrenado_completo.pkl  
historial_metricas.pkl 

El primero contiene las estrategias aprendidas.
El segundo  almacena las métricas recogidas durante el entrenamiento.


Posteriormente, para visualizar estas métricas, se debe ejecutar:
python graficar_metricas.py
Esto mostrará gráficas sobre la evolución del regret, la media del payoff y la estabilidad del comportamiento del agente.


### 4. Interfaz Visual del Sistema (Frontend)
El sistema cuenta con una interfaz HTML completa que guía al usuario desde la introducción hasta la visualización de estadísticas y recomendaciones:
•	portada.html, loader.html, inicial.html, partida.html, stats.html, rec.html → gestionan el flujo visual del juego.
•	game.js → ejecuta la lógica interactiva del frontend, coordinándose con el servidor Flask.
•	Archivos .css → definen el estilo visual de la interfaz.
Estas vistas permiten al usuario jugar, ver resultados, revisar estadísticas y obtener recomendaciones de forma estructurada y pedagógica.
