# Tarea 04 — Duración natural y panel avanzado
Estado: completado

## Objetivo
Eliminar el límite corto de duración incorporado inicialmente y simplificar la pantalla principal. Conservar todos los parámetros técnicos dentro de un desplegable Avanzado.

## Implementación
- Quitado `semantic_max_tokens=384` de las solicitudes ordinarias.
- Se delega el final a EOS; el backend aplica su máximo de seguridad por defecto de 9000 tokens semánticos (~360 segundos a 25 tokens/s), sin garantía de llegar a ese máximo.
- El usuario puede activar opcionalmente un techo manual en Avanzado.
- Avanzado incluye CoT, semilla, pasos NAR, CFG, temperatura, top-p/top-k, penalización y ventana semántica, mínimo de tokens, muestreo ABC.
- Pantalla principal: estilo, letra, botón, WAV y descarga.
- Se lanzó nueva UI en puerto 7877, conservando la anterior 7875 sin detenerla. Ambas usan motor 7876.

## Validación
- Ocho tests unitarios correctos.
- Comprobado que la solicitud por defecto no transmite `semantic_max_tokens`.
- Puerto 7877 responde HTTP 200, servidor CUDA HTTP 200 y modelo Q8 cargado.
- Se probó generación WAV de 6.4 segundos con una solicitud corta limitada expresamente a 160 tokens antes del cambio. Una canción larga hasta EOS aún no se ha probado de extremo a extremo.
