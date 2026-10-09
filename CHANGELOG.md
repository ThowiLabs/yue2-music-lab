# Historial de versiones

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
