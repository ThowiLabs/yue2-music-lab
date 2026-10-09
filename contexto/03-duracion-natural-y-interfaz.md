# Fecha
2026-10-08 America/Merida (2026-10-09 UTC)

# Objetivo
Permitir canciones completas sin el límite artificial de aproximadamente 15 segundos y simplificar Gradio.

# Decisiones tomadas
- El ajuste anterior `semantic_max_tokens=384` correspondía a ~15.36 s con 25 tokens/s; se eliminó de las solicitudes predeterminadas.
- El motor documenta `semantic_max_tokens=9000` de fábrica; EOS puede cortar antes del techo (máximo técnico, no duración garantizada).
- Límite manual opcional desde Avanzado, desactivado por defecto.
- UI principal mínima y parámetros no esenciales en `gr.Accordion(open=False)`.
- No se interrumpió la Gradio activa 7875; nueva UI 7877 usa backend 7876.

# Arquitectura actual
YuE2 Q8 Gradio 7877 -> API CUDA local 7876 -> GGUF Q8 + VAE F16 -> WAV reproducible/descargable. UI anterior aún activa 7875.

# Librerías usadas
Gradio 6.x, Python stdlib, audio.cpp v0.9.0 CUDA.

# Archivos importantes modificados
`app.py`, `tests/test_studio.py`, README y archivos Ponytail de contexto/tareas.

# Problemas encontrados
El valor elegido de 384 tokens causaba canciones cortas, no un límite inevitable del modelo. Gradio con autenticación devuelve 401 en /config sin sesión, comportamiento previsto.

# Soluciones implementadas
Se omite `semantic_max_tokens` normalmente; se permite control avanzado explícito validado. Pruebas de ensamblado y HTTP realizadas.

# Pendientes
Escuchar y validar una canción completa hasta EOS con letras de longitud real. Verificar duración, afinación y consumo VRAM en las T4.

# Próximos pasos
Probar nueva UI 7877. Usar Git para versionar cambios y crear entrega ZIP completa.
