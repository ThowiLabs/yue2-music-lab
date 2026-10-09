# Fecha
2026-10-09

# Objetivo
Desactivar temporalmente la autenticación de YuE2 Music Lab por petición explícita del usuario, conservando la posibilidad de restaurar el login sin perder secretos ni reiniciar el motor CUDA.

# Decisiones
- La variable de entorno GRADIO_DISABLE_AUTH=1 desactiva login SOLO en la instancia Gradio que se arranque con ella.
- Sin esta variable, login continúa obligatorio como antes.
- No tocar .gradio-auth, modelos, outputs ni motor audio.cpp.
- El acceso externo con túnel temporal gradio.live es público cuando se desactiva el login.

# Arquitectura
studio_fl.py en 0.0.0.0:7875 -> audio.cpp YuE2 CUDA en 127.0.0.1:7876.

# Librerías
Gradio, Python, audio.cpp precompilado; no nuevas dependencias.

# Archivos modificados
studio_fl.py, tests/test_flstudio.py, README.md, CHANGELOG.md y scripts/package.py.

# Problemas y solución
Desactivar login en una URL pública permite a terceros usar GPU y acceder a archivos que expone el panel; se señala expresamente y se conserva login obligatorio por defecto. Cambio reversible reiniciando Gradio sin variable.

# Validación
18 pruebas unitarias satisfactorias, incluida comprobación de ambos modos de autenticación.

# Pendientes
Reactivar login cuando el usuario termine las pruebas.
