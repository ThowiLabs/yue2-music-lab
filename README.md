# YuE2 Q8 Studio — Kaggle Tesla T4

Interfaz Gradio para generación musical con [YuE2-3B-GGUF](https://huggingface.co/audio-cpp/Yue2-3B-GGUF) Q8_0 y VAE F16, usando el servidor nativo de [audio.cpp](https://github.com/0xShug0/audio.cpp) compilado previamente para CUDA 12.8.

## Requisitos

- Kaggle Linux x86_64 con GPU Tesla T4, CUDA 12.8 y bibliotecas del driver NVIDIA accesibles en `/usr/local/nvidia/lib64`.
- Python 3.10 o superior, `curl` y conexión a Hugging Face/GitHub.
- Espacio para los GGUF (~4.3 GiB) y el servidor (precompilado de ~261 MiB extraído).
- Cuenta y sesión Kaggle con GPU activada. La sesión puede expirar; Gradio Share no es alojamiento persistente.

## Instalación y arranque

```bash
cd /kaggle/working/yue2-q8-gradio
python -m pip install -r requirements.txt
python scripts/install.py
python scripts/run.py
```

El instalador usa primero el precompilado oficial `audio.cpp v0.9.0` para **Ubuntu x64 + CUDA 12.8**, sin compilación local. Verifica el SHA-256 del release. Descarga exclusivamente estos archivos de `audio-cpp/Yue2-3B-GGUF`:

- `yue2-3b-q8_0.gguf`
- `yue2-vae-f16.gguf`
- `sidecars/yue2-model-config.json`
- `sidecars/yue2-generation-config.json`
- `sidecars/yue2-qwen.tiktoken`
- `sidecars/yue2-vae-config.json`

`scripts/run.py` prepara `server.json` de forma local, configura `LD_LIBRARY_PATH` solo para los subprocesos, inicia la API en `127.0.0.1:7876` y Gradio en `0.0.0.0:7875`. La API no se expone externamente. La UI sí puede compartir enlace temporal; siempre requiere autenticación. La primera ejecución crea `.gradio-auth` (modo 0600, fuera de Git); para leerla: `cat .gradio-auth`. También puedes configurar `GRADIO_USER` y `GRADIO_PASSWORD` mediante variables de entorno.

Si ya están ocupados los puertos, el lanzador no interrumpe otros servicios. Cambia `GRADIO_SERVER_PORT` y `YUE2_BACKEND_PORT` si necesitas puertos alternativos. Reutiliza la API local existente únicamente cuando contiene el modelo `yue2-q8`.

La generación utiliza **una Tesla T4 (GPU 0)** y deja la segunda disponible; el servidor detectó ambas. Si el motor necesita reiniciarse, detén únicamente los procesos propios de YuE2, nunca los servicios MCP u otros estudios musicales.

## Uso

Introduce estilo musical y letra etiquetada (`[Verse]`, `[Chorus]`) en la pantalla principal y pulsa **Generar canción completa**. El resultado aparece como reproductor WAV y archivo descargable. Despliega **Avanzado · ajustes del modelo** para ajustar planificación `off`, `melody` o `full`, semilla, pasos NAR, CFG, parámetros semánticos (temperatura, top-p, top-k, penalización y ventana), parámetros ABC y un límite manual opcional.

**Duración natural:** no se envía `semantic_max_tokens` de forma predeterminada. El motor finaliza cuando predice EOS o alcanza su máximo de seguridad original de **9000 tokens semánticos** (~6 minutos a 25 tokens/s). La canción puede durar menos; no es un generador de duración ilimitada. El valor anterior de 384 tokens cortaba el audio a ~15 segundos y se eliminó. No hay streaming del WAV mientras se genera.

**Despliegue de prueba:** para conservar una sesión existente, la nueva interfaz se inició en `7877`, manteniendo la anterior en `7875`; ambas usan la API `7876`. Al iniciar desde cero, `scripts/run.py` usa por defecto `7875` y se niega a ocupar un puerto utilizado.

**Idiomas:** el modelo YuE2 documenta principalmente inglés; probar letras en español es experimental y no garantiza pronunciación ni calidad.

## Pruebas y diagnóstico

```bash
python -m unittest discover -s tests -v
python scripts/smoke.py       # prueba GPU real; requiere API activa
curl -fsS http://127.0.0.1:7876/health
curl -fsS http://127.0.0.1:7876/v1/models
```

Revisar `logs/backend.log` (si se ejecutó con el lanzador) y `logs/smoke.log` para diagnóstico. Los pesos y la interfaz conservan los audios en `outputs/`; los modelos, audios, logs, credenciales y binarios están excluidos de Git y del paquete de entrega. Para iniciar desde un clon, se regeneran ejecutando la instalación.

## Licencias y límites

YuE2-3B-GGUF publica licencia **CC BY-NC 4.0**: comprobar las condiciones de uso antes de cualquier fin comercial. El motor audio.cpp tiene su propia licencia y dependencias. Verificar licencias de cada artefacto por separado.

El ZIP de entrega incluye el código completo, `.git/`, `contexto/` y `tareas/`, pero no los varios gigabytes de pesos ni binarios regenerables. Los commits son en español.

## Control de versiones

```bash
git status
git log --oneline --decorate
# Consultar versiones anteriores sin perder el estado actual:
git show <commit> --stat
```

Estructura: `app.py` (Gradio + API), `scripts/install.py` (precompilado y pesos), `scripts/run.py` (arranque seguro), `scripts/smoke.py` (generación breve), `tests/` (pruebas), `contexto/` (continuidad), `tareas/` (seguimiento).
