# build_exe.py

import sys
from PyInstaller.__main__ import run

if __name__ == '__main__':
    # Lista de recursos a incluir (origen;destino)
    datas = [
        "cfr_entreno.pkl;.",
        "index.html;.",
        "inicial.html;.",
        "partida.html;.",
        "Nash.png;.",
        "mesa.png;.",
        "card_back.png;.",
        "last_hand.log;.",
        "cards;cards"
        
        
    ]

    # Convertimos a la forma que PyInstaller espera: ['--add-data', 'origen;destino', ...]
    add_data_args = []
    for item in datas:
        add_data_args += ["--add-data", item]

    # Construimos la lista de argumentos para PyInstaller
    opts = [
        "--onefile",
        # Si quieres que la consola permanezca visible cuando ejecutes el .exe, quita "--noconsole".
        "--noconsole",
    ] + add_data_args + [
        "run_app.py"   # aquí "run_app.py" es el script principal de tu app Flask
    ]

    # Llamamos a PyInstaller
    run(opts)
