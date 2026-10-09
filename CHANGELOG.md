# Historial de versiones

## v0.3.0 — 2026-10-09
- Estudio unificado con cuatro modos: crear, cover/remix de FL Studio, extender WAV externo y continuar tokens semánticos YuE2.
- Covers desde un único WAV/MP3 + letra: extracción melódica automática; MIDI/ABC y análisis previo opcionales.
- Introducido análisis aproximado de tonalidad/tempo/melodía con librosa, MIDI con music21, ensamblado WAV con FFmpeg y crossfade.
- Exportación de tokens semánticos para futuras extensiones; backend YuE2 conserva final natural EOS para creación ordinaria.
- Procesos Gradio antiguos cerrados y una sola instancia publicada en 7875, API en 7876.
- Pruebas automatizadas de generación, carga de WAV, MIDI, ABC, cover sin partitura y tokens. Modelo y archivos originales conservados.

## v0.2.1 — 2026-10-09
- Valores iniciales rápidos en el código: CoT off, NAR 4, CFG 1.00.
- Los demás controles avanzados se mantienen y EOS natural permanece activo.
- Nueve pruebas completadas, incluida comprobación de defaults Gradio.
- Las instancias originales 7875, 7876 y 7877 no fueron reiniciadas.

## v0.2.0 — 2026-10-08
- Retirado el límite artificial de 384 tokens (~15 segundos) en generación ordinaria.
- El motor espera su token de fin (EOS) respetando el techo interno de seguridad de 9000 tokens (~6 min).
- UI minimalista con apartado Avanzado desplegable y límites opcionales.
- Implementada validación de parámetros, autenticación Gradio y 8 pruebas automáticas.
- Se levantó puerto 7877 sin detener la interfaz anterior 7875.

## v0.1.0 — 2026-10-08
- Proyecto autónomo Ponytail con Git y contexto/tareas.
- Precompilado oficial audio.cpp v0.9.0 CUDA 12.8 SHA-256 verificado.
- Descarga modelo YuE2 Q8_0 y VAE F16 de Hugging Face, API HTTP local.
- Dos Tesla T4 reconocidas; Gradio inicial y smoke test WAV satisfactorio.

## Operación
Las versiones se identifican con `git tag`; nunca se deben versionar pesos, WAV, secretos o binarios regenerables.
