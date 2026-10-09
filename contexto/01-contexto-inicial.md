# Fecha
2026-10-08 (America/Merida)

# Objetivo
Instalar YuE2-3B Q8_0 + VAE F16 de audio-cpp/Yue2-3B-GGUF con Gradio en Kaggle 2x Tesla T4, proyecto aislado.

# Decisiones tomadas
- Usar el runtime oficial 0xShug0/audio.cpp con familia yue2.
- Repositorio independiente en /kaggle/working/yue2-q8-gradio, rama main y commits en español.
- No modificar proyectos o instancias Gradio anteriores; no tocar lilith-mcp, lilith-cl, puertos 8080, 7870-7872, 8085, 8087.
- Usar puerto 7875 si está libre. Bind 0.0.0.0 con Gradio compartido opcional.
- GPU: el shell MCP no define LD_LIBRARY_PATH. Con /usr/local/nvidia/lib64:/usr/local/cuda/lib64, torch detectó Tesla T4 x2; no modificar la infraestructura MCP.
- El contexto del proyecto ACE-Step aportó reglas de seguridad y operación, pero YuE2 es independiente.
- No versionar modelos, WAV/MP3, dependencias, logs ni secretos.

# Arquitectura actual
Gradio en Python llama por proceso al CLI de audio.cpp; archivos de modelo Hugging Face descargados fuera de Git.

# Librerías usadas
Python 3, gradio, huggingface_hub; motor C++/CUDA audio.cpp y dependencias nativas.

# Archivos importantes modificados
Este documento, tareas numeradas, README, scripts de instalación/ejecución y pruebas por crear.

# Problemas encontrados
El driver CUDA no está en la ruta de librerías predeterminada; se comprobó que existe y funciona al añadir LD_LIBRARY_PATH al proceso.

# Soluciones implementadas
Carpeta de proyecto aislada; detección de GPU con entorno temporal.

# Pendientes
Descargar Q8 + VAE + sidecars, compilar CLI, instalar interfaz y validar una generación musical real.

# Próximos pasos
Crear tareas, descargar y compilar, probar Gradio y efectuar smoke test sin tocar procesos preexistentes.
