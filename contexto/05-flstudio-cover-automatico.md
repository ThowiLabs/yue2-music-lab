# Fecha
2026-10-09

# Objetivo
Permitir covers de ideas FL Studio con solamente un audio WAV/MP3 y la letra, sin exigir MIDI ni escritura manual de partituras ABC.

# Decisiones tomadas
- Mantener YuE2/audio.cpp como motor principal en GPU 0, API 127.0.0.1:7876.
- Añadir interfaz unificada studio_fl.py en un único Gradio 0.0.0.0:7875.
- Pestaña Cover/Remix: WAV/MP3, letra, estilo y botón principal. Si no se proporciona ABC manual, analizar automáticamente el audio con librosa para obtener la referencia ABC.
- MIDI/ABC, análisis previo y NAR/CFG quedan en un acordeón avanzado y son opcionales.
- Si cambia la referencia WAV/MIDI, borrar la partitura calculada previamente para evitar usar otra canción por accidente.
- La misma regla opcional se aplica al flujo Extender: extraer los últimos compases si la partitura no fue proporcionada.
- El archivo ABC de referencia se guarda junto al WAV generado; los tokens semánticos se exportan cuando el motor los devuelve.

# Arquitectura actual
Gradio studio_fl.py 7875 -> audio.cpp CUDA 7876 -> GGUF YuE2 Q8 y VAE F16 originales.
flstudio_tools.py procesa el archivo local usando FFmpeg/librosa/music21 y crea ABC.
El sistema NO pasa ondas WAV externas directamente al modelo, por lo que un cover es una interpretación generada.

# Librerías usadas
Gradio 6, huggingface_hub, NumPy, SciPy, librosa, soundfile, music21, FFmpeg y ffprobe instalados en Kaggle.

# Archivos importantes modificados
studio_fl.py, flstudio_tools.py, tests/test_flstudio.py, tests/test_studio.py, requirements.txt, README.md, CHANGELOG.md, scripts/run.py, scripts/package.py, scripts/smoke_cover_auto.py, scripts/smoke_fl.py, scripts/smoke_continue_fl.py, app.py.

# Problemas encontrados
- El motor no codifica un WAV externo como tokens semánticos nativos; usamos melodía/ABC aproximada en covers.
- Un análisis previo queda obsoleto si el usuario cambia de archivo; la UI borra el ABC.
- El software de transcripción estima la melodía del pico espectral principal en una mezcla; instrumentos y voces simultáneos pueden producir notas erróneas.

# Soluciones implementadas
- Pista de referencia analizada automáticamente al pulsar Crear cover; el usuario no necesita partitura.
- El código conserva y valida ABC manual opcional y prioriza MIDI cuando está presente.
- Test unitario de WAV + letra sin MIDI/ABC y validación de ABC manual.
- Prueba real 2026-10-09: WAV sintetizado localmente -> análisis automático de tempo/tonalidad/ABC -> API YuE2 -> WAV de 8.8 s en 4.8 s, exportando tokens.
- Suite de 17 pruebas correctas.

# Pendientes
- Comprobar fidelidad con un WAV auténtico y musicalmente complejo de FL Studio.
- Considerar SheetSage2/Basic Pitch u otro extractor robusto si la calidad del cover no es suficiente, respetando primero precompilados.
- Añadir más controles de selección de fragmento/segmentación solo cuando sea necesario.

# Próximos pasos
Comparar resultados reales del usuario y mejorar detección de melodía multitrack usando MIDI opcional.
