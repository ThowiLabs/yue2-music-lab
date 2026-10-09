# Fecha
2026-10-09

# Objetivo
Dejar ajustes rápidos de YuE2 como valores predeterminados sin tocar las instancias activas, y evaluar motor alternativo de manera aislada.

# Decisiones tomadas
- CoT=off, NAR=4, CFG=1.0 para solicitudes nuevas de la interfaz cuando se vuelva a iniciar.
- Conservados los demás controles y el límite manual desactivado, por lo que sigue EOS natural.
- Las instancias Gradio en 7875 y 7877 y el motor en 7876 siguen ejecutándose con su código cargado anterior.
- El motor alternativo HOT-Step se despliega en un repositorio separado en /kaggle/working/yue2-hotstep-lab.

# Arquitectura actual
Gradio en app.py → API audio.cpp CUDA en 127.0.0.1:7876 → GGUF original.

# Librerías usadas
Gradio, Python estándar, audio.cpp precompilado v0.9.0 CUDA.

# Archivos importantes modificados
app.py y tests/test_studio.py.

# Problemas encontrados
El GGUF descargado declara general.architecture=audiocpp; los motores alternativos usan conversión GGUF propia. No asumir compatibilidad binaria.

# Soluciones implementadas
Defaults rápidos en código y test que inspecciona los controles Gradio.

# Pendientes
Comprobar si el motor HOT-Step admite el GGUF existente sin modificación; si no, documentar limitación sin redescargar pesos inadvertidamente.

# Próximos pasos
Levantar motor compatible en un puerto aislado, sin detener servicios actuales.
