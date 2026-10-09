# YuE2 Q8 Studio — Kaggle Tesla T4

Interfaz Gradio para generación musical con [YuE2-3B-GGUF](https://huggingface.co/audio-cpp/Yue2-3B-GGUF) Q8_0 y VAE F16, usando el servidor nativo de [audio.cpp](https://github.com/0xShug0/audio.cpp) compilado previamente para CUDA 12.8.

## Music Lab para proyectos de FL Studio (v0.3.0)

La interfaz principal ahora es `studio_fl.py`: `python scripts/run.py` inicia un solo Gradio en `0.0.0.0:7875` (si el puerto está libre) y la API YuE2 en loopback `127.0.0.1:7876`. Para arrancar el panel con una API ya encendida, ejecutar `GRADIO_SERVER_PORT=7875 python -u studio_fl.py`. `app.py` permanece como implementación clásica de referencia y origen de la validación y credenciales; no se inicia como segundo panel.

El estudio dispone de cuatro pestañas:

1. **Crear canción**: letra y estilo → WAV; al finalizar guarda también `.semantic.json` para continuar generaciones. Con CoT melody/full puede exportar partitura ABC.
2. **Cover / Remix**: subir tu WAV/MP3/FLAC/OGG/M4A de FL Studio, escribir la letra y pulsar **Crear cover**. La melodía se analiza automáticamente; **NO se requiere MIDI, escribir ABC ni pulsar Analizar**. MIDI, ABC y análisis manual quedan en un acordeón opcional para mejorar precisión. El modelo no conserva la voz ni el sonido exacto de los instrumentos originales.
3. **Extender FL Studio**: subir mezcla WAV/MP3; si no se proporciona MIDI/ABC o una partitura manual, se analizan automáticamente los últimos ~24 segundos al generar; describir qué tocar a continuación; generar una sección nueva y unirla conservando el archivo original mediante crossfade configurable. No es extensión nativa de la onda, por lo que se puede notar un cambio de timbre. La duración objetivo es un techo, no una promesa de duración exacta.
4. **Continuar una canción YuE2**: cargar el JSON de tokens semánticos que guardó nuestro panel para extender auténticamente su historia musical; no acepta el WAV externo como prefijo semántico. Los tokens existentes se vuelven a sintetizar, por lo que el inicio puede sonar un poco distinto.

**Importante para FL Studio:** exportar un `*.mid` de la melodía principal desde el proyecto, además de tu `*.wav`, ofrece un cover compositivamente mucho más preciso. Extraer automáticamente melodía de una mezcla polifónica es una estimación heurística en CPU (librosa, análisis de tempo y tonalidad, detección de picos); no es SheetSage2. Los análisis solo utilizan los primeros ~24 segundos elegidos o los últimos ~24 segundos en la pestaña de extensión. No se descargan modelos extra de transcripción ni se envían tus canciones a servicios externos, salvo que uses los propios túneles remotos para subir archivos al panel.

**Pruebas reales verificadas:**

- Condicionamiento ABC externo: 8.8 s de audio con WAV y JSON de 220 tokens en 5.8 s de inferencia.
- Continuación mediante `semantic_prefix`: 220 → 440 tokens, WAV de 17.6 s en 5.4 s de inferencia.
- Unión de archivos: WAV de 3.0 s + WAV de 2.0 s con crossfade de 0.5 s = 4.5 s resultantes.
- Pruebas automatizadas: `python -m unittest discover -s tests -v`.
- Pruebas GPU cortas (requieren API en 7876): `python scripts/smoke_fl.py`, `python scripts/smoke_continue_fl.py`.

El acceso remoto conserva autenticación Gradio con credenciales del proyecto original en el archivo local `.gradio-auth`, fuera de Git. Se cerraron paneles y túneles anteriores antes de iniciar una única instancia limpia en 7875. HOT-Step queda instalado en otra carpeta; se cerró su **panel Gradio**, sin eliminar modelos ni apagar necesariamente su motor nativo.

**Dependencias de procesamiento local:** `ffmpeg`, `ffprobe`, NumPy, scipy, librosa, soundfile y music21 (ya disponibles en la instancia probada). No es imprescindible instalar SheetSage2 para estos flujos experimentales.

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

**Despliegue actual:** el panel Music Lab nuevo se ejecuta únicamente en `7875`; se cerraron las antiguas instancias Gradio y túneles en `7877` y `7879`. La API YuE2 continúa en `7876`.

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

Estructura: `studio_fl.py` (Music Lab unificado), `flstudio_tools.py` (WAV/MP3, MIDI, ABC, crossfade), `app.py` (interfaz clásica y validación), `scripts/install.py` (precompilado y pesos), `scripts/run.py` (arranque seguro), `scripts/smoke_fl.py` y `scripts/smoke_continue_fl.py` (generación y continuación reales), `tests/` (pruebas), `contexto/` (continuidad), `tareas/` (seguimiento).
