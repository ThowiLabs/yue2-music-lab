# Fecha
2026-10-09

# Objetivo
A petición del usuario, la celda de arranque de Kaggle debe permanecer en estado Running mientras YuE2/Gradio está activo, mostrar logs en vivo y detener la instancia al interrumpir la ejecución. Eliminar consultas y apagado separados.

# Decisiones
- Notebook Kaggle con seis pasos y 12 celdas (seis markdown + seis código).
- Última celda: inicia scripts/run.py con Popen, stdout=PIPE, stderr=STDOUT, text=True, bufsize=1 y PYTHONUNBUFFERED=1; consume el flujo de salida y espera síncronamente hasta que termine el servidor.
- start_new_session=True para agrupar subprocesos de una única instancia; al recibir KeyboardInterrupt se envía SIGTERM al grupo del proceso y, si no termina, SIGKILL después de 12 segundos.
- No iniciar un daemon en segundo plano ni escribir un log externo para la salida de Gradio. Se muestra el enlace en el output de la misma celda.
- Se eliminan las celdas #7 de comprobación de logs y #8 de apagado porque ya no tienen sentido.
- Si GRADIO_PORT está ocupado, el notebook muestra un error sin detener ni modificar servicios externos.

# Archivos
kaggle/YuE2_Music_Lab_ThowiLabs.ipynb, tests/test_kaggle_notebook.py, README.md, CHANGELOG.md, scripts/package.py.

# Pruebas
Se validó la sintaxis de todas las celdas con ast y un proceso ficticio en una sesión aislada; al recibir SIGINT el notebook mostró salida en vivo y finalizó ambos procesos iniciados con 'Servicio detenido.'. Los servicios CUDA existentes no se tocaron.

# Próximos pasos
Publicar el repositorio vacío thowilabs/yue2-music-lab a partir del ZIP y ejecutar el notebook en Kaggle con GPU e Internet activados.
