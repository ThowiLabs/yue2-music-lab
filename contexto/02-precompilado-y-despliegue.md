# Fecha
2026-10-08 (America/Merida), 2026-10-09 UTC

# Objetivo
Evitar compilación innecesaria mediante distribución oficial CUDA y levantar YuE2 Q8 con Gradio.

# Decisiones tomadas
- Preferir un precompilado oficial compatible antes de compilar. Revisar releases de nuevo en proyectos futuros.
- Seleccionado audio.cpp v0.9.0, `audio-v0.9.0-bin-ubuntu-x64-cuda12.8-colab.tar.gz`, 224004027 bytes, SHA-256 `c9ed906f918246669c324f0d31f1b7dd80cbe003c35cf8a54932f333b57ca3f6`.
- El release contiene `audiocpp_server`, no `audiocpp_cli`; se utiliza su API `POST /v1/tasks/run` desde Gradio.
- API solo en 127.0.0.1:7876 y Gradio protegido con credenciales en 0.0.0.0:7875, compartición temporal opcional.
- Una T4 para inferencia por defecto. No tocar servicios externos.

# Arquitectura actual
Gradio `app.py` -> JSON local `/v1/tasks/run` -> audio.cpp precompilado -> YuE2 3B Q8_0 y VAE F16 -> WAV Base64 -> `outputs/*.wav`.

# Librerías usadas
Gradio 6.x, huggingface_hub 1.x/2.x, Python stdlib. Backend nativo audio.cpp 0.9.0 CUDA 12.8.

# Archivos importantes modificados
`app.py`, `scripts/install.py`, `scripts/run.py`, `scripts/smoke.py`, `requirements.txt`, `.env.example`, `README.md`, `tests/`, `.gitignore`.

# Problemas encontrados
`LD_LIBRARY_PATH` vacío ocultaba CUDA aunque había /dev/nvidia0/1 y driver instalado. Una compilación CMake previa falló por ausencia del target `CUDA::cuda_driver`; no se insistió tras encontrar precompilado. Clonar el submódulo frontend intentó SSH; no se necesita para usar binario precompilado.

# Soluciones implementadas
Driver visible a través de variables de entorno por proceso. Precompilado SHA-256 verificado. GPU CUDA 0 y 1 Tesla T4 detectadas por `audiocpp_server --list-devices`. Descargados 6 archivos Q8/VAE/sidecars. API de servidor inició correctamente y contestó /health y /v1/models.

# Pendientes
Prueba real de generación breve y verificación final del paquete ZIP. En Kaggle el enlace Gradio temporal depende de la sesión activa.

# Próximos pasos
Probar WAV, ejecutar unit tests, commit español, exportar ZIP con historia Git.
