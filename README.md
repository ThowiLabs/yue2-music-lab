# YuE2 Music Lab

**Estudio de generación musical con YuE2-3B Q8, CUDA y una interfaz web en Gradio.**

Proyecto de [ThowiLabs](https://github.com/thowilabs) para crear canciones desde letras y descripciones musicales, experimentar con covers/remixes de proyectos de FL Studio y continuar generaciones mediante tokens semánticos de YuE2.

> **Estado:** funcional para generación musical y continuación semántica. Los covers, remixes y extensiones a partir de archivos WAV/MP3 externos son **experimentales**: no reproducen exactamente la voz, la forma de cantar ni el arreglo original. No es un reemplazo directo de las herramientas Cover/Extend de Suno.

## Contenido

- [Características](#características)
- [Cómo funciona](#cómo-funciona)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Cuaderno Kaggle](#cuaderno-kaggle)
- [Publicación en GitHub](#publicación-en-github)
- [Configuración y seguridad](#configuración-y-seguridad)
- [Guía de uso](#guía-de-uso)
- [Limitaciones conocidas](#limitaciones-conocidas)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Pruebas](#pruebas)
- [Problemas comunes](#problemas-comunes)
- [Licencias y créditos](#licencias-y-créditos)

## Características

| Módulo | Función | Estado |
| --- | --- | --- |
| **Crear canción** | Generación de música desde estilo y letra; exportación WAV | Funcional |
| **Cover / Remix** | Subir WAV/MP3, escribir letra y generar otra interpretación con una melodía extraída automáticamente | Experimental |
| **Extender FL Studio** | Analizar el final de un archivo, generar una sección adicional y unir ambas mediante crossfade | Experimental |
| **Continuar YuE2** | Continuar una canción creada por YuE2 usando su archivo de tokens semánticos JSON | Funcional |
| **MIDI / ABC** | Proporcionar una melodía más precisa, opcional para covers y extensiones | Funcional |
| **GPU CUDA** | Inferencia con motor nativo `audio.cpp` y pesos GGUF Q8_0 | Probado en Tesla T4 |
| **Acceso web** | Gradio, archivos WAV descargables y autenticación configurable | Funcional |

El proyecto utiliza **YuE2-3B Q8_0** y su **VAE F16**, evitando cargar un modelo distinto para cada pestaña.

## Cómo funciona

```text
                   YuE2 Music Lab (Gradio)
                      0.0.0.0:7875
                            |
             +--------------+--------------+
             |              |              |
         Crear música   Cover / Remix    Extender FL
             |              |              |
      Estilo + letra    WAV/MP3/MIDI     WAV/MP3/MIDI
             |              |              |
             |        Análisis melódico   Análisis final
             |          -> ABC aprox.     -> ABC aprox.
             +--------------+--------------+
                            |
                   audio.cpp + CUDA
                     127.0.0.1:7876
                            |
                 YuE2-3B Q8 + VAE F16
                            |
                       Audio WAV
                            |
                    Tokens semánticos
                    (opcional, JSON)
                            |
                    Continuar YuE2
```

**Importante:** los WAV/MP3 externos **no se convierten en tokens semánticos reales del modelo**. El módulo de covers estima notas musicales y crea una referencia ABC. Solo las generaciones que conservan sus tokens JSON admiten continuación semántica nativa.

## Requisitos

- **Sistema:** Linux x86_64. Desarrollo y pruebas realizados en **Kaggle con NVIDIA Tesla T4**.
- **GPU:** NVIDIA compatible con CUDA y memoria suficiente para cargar YuE2-3B Q8 y la VAE; la configuración validada usa **CUDA 12.8**.
- **Python:** 3.10 o posterior.
- **Sistema:** `git`, `curl`, `ffmpeg` y `ffprobe` disponibles en `PATH`.
- **Red:** acceso a GitHub y Hugging Face durante la instalación.
- **Almacenamiento:** varios gigabytes para modelos GGUF, motor, caché y resultados.

El proyecto utiliza un **precompilado oficial de audio.cpp v0.9.0** para Ubuntu x64 CUDA 12.8. No se ha validado esta configuración en Windows, macOS ni dispositivos móviles.

## Instalación

### 1. Clonar el proyecto

```bash
git clone https://github.com/thowilabs/yue2-music-lab.git
cd yue2-music-lab
```

> El enlace de clonación estará disponible cuando el repositorio se publique en la cuenta ThowiLabs.

### 2. Instalar dependencias Python

Se recomienda un entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

En sistemas Debian/Ubuntu, instalar FFmpeg mediante el gestor de paquetes si no está presente:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg curl
```

### 3. Descargar el motor y los modelos

```bash
python scripts/install.py
```

El instalador:

1. Descarga el release oficial `audio.cpp v0.9.0` para CUDA 12.8 y **verifica su SHA-256**.
2. Instala `audiocpp_server` y la especificación de YuE2.
3. Descarga `yue2-3b-q8_0.gguf`, `yue2-vae-f16.gguf` y los archivos auxiliares desde [audio-cpp/Yue2-3B-GGUF](https://huggingface.co/audio-cpp/Yue2-3B-GGUF).
4. Comprueba la presencia de todos los archivos requeridos.

**Los pesos y binarios no se incluyen en este repositorio.** La instalación depende de los archivos y licencias publicados por sus autores.

### 4. Iniciar el estudio

```bash
python scripts/run.py
```

Dirección local de la interfaz:

```text
http://127.0.0.1:7875
```

El motor se conecta internamente mediante `http://127.0.0.1:7876`; por diseño, **no se expone la API de inferencia a la red**.

Para detener el arranque administrado, usa `Ctrl+C`. El lanzador comprueba que los puertos no estén ocupados antes de iniciar nuevos procesos.

## Cuaderno Kaggle

El proyecto incluye [**`kaggle/YuE2_Music_Lab_ThowiLabs.ipynb`**](kaggle/YuE2_Music_Lab_ThowiLabs.ipynb), listo para importarse en Kaggle mediante **File → Import Notebook** o cargándolo desde el dispositivo. El cuaderno:

1. Comprueba el acelerador GPU y el sistema operativo.
2. Ejecuta `git clone https://github.com/thowilabs/yue2-music-lab.git` (o actualiza un clon existente sin sobreescribirlo).
3. Instala las dependencias Python y FFmpeg si falta.
4. Descarga y verifica el motor CUDA y los pesos YuE2 Q8.
5. Arranca el panel Gradio, ofrece el enlace temporal y permite controlar el modo de autenticación.

**Antes de ejecutarlo:** publica el repositorio en la ruta indicada, habilita **GPU** e **Internet** en *Kaggle Notebook Settings* y acepta el espacio necesario para los pesos. El notebook tiene login habilitado por defecto por seguridad.

## Publicación en GitHub

Este proyecto se prepara para el repositorio **`thowilabs/yue2-music-lab`**, con rama **`main`**. Créalo **vacío**, sin añadir README, LICENSE ni .gitignore desde GitHub, porque el ZIP ya contiene el historial Git local. Tras extraer el ZIP y entrar en la carpeta que contiene `.git/`:

```bash
git remote add origin https://github.com/thowilabs/yue2-music-lab.git
git push -u origin main
git push origin --tags
```

Se solicitará autenticación GitHub de acuerdo con tu configuración. Si el repositorio ya tiene un remoto `origin`, revisa `git remote -v` antes de modificarlo. **No uses `git push --force`**. Los archivos `.gradio-auth`, modelos GGUF, audios y binarios quedan excluidos del control de versiones.

## Configuración y seguridad

Variables opcionales de entorno (consulta [`.env.example`](.env.example)):

| Variable | Predeterminado | Descripción |
| --- | --- | --- |
| `GRADIO_SERVER_PORT` | `7875` | Puerto de la interfaz |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | Dirección de escucha de Gradio |
| `YUE2_BACKEND_PORT` | `7876` | Puerto local de la API CUDA al usar el lanzador |
| `GRADIO_SHARE` | `1` | Crear un túnel temporal `gradio.live` |
| `GRADIO_USER` | `admin` | Usuario de acceso |
| `GRADIO_PASSWORD` | Generada en primer inicio | Contraseña, si se configura explícitamente |
| `GRADIO_DISABLE_AUTH` | `0` | **`1` deshabilita toda la autenticación**, solo para pruebas |
| `YUE2_API_URL` | `http://127.0.0.1:7876` | API a la que se conecta el panel |

La primera ejecución crea una contraseña aleatoria en `.gradio-auth` con permisos restrictivos. **No publiques ese archivo ni compartas su contenido.**

Para trabajar **sin enlace público**:

```bash
GRADIO_SHARE=0 python scripts/run.py
```

Para habilitar **temporalmente el acceso sin login**:

```bash
GRADIO_DISABLE_AUTH=1 python scripts/run.py
```

Para restaurarlo:

```bash
GRADIO_DISABLE_AUTH=0 python scripts/run.py
```

**Advertencia:** si combinas `GRADIO_SHARE=1` y `GRADIO_DISABLE_AUTH=1`, cualquier persona con la URL podrá utilizar la GPU y subir o consultar archivos accesibles desde el panel. Se recomienda mantener la autenticación activada, especialmente en enlaces públicos.

**Nota:** las variables del archivo `.env.example` no se cargan automáticamente; se exportan en el entorno o se pasan al comando de ejecución. La ejecución directa de `studio_fl.py` requiere que la API YuE2 esté iniciada.

## Guía de uso

### Crear canción

1. Abrir **Crear canción**.
2. Introducir una descripción de género, instrumentos y producción.
3. Escribir la letra usando etiquetas como `[verse]`, `[chorus]` o `[bridge]`.
4. Pulsar **Generar canción** y descargar el WAV.

Los ajustes iniciales son **CoT off, NAR 4 y CFG 1.0**. En el apartado avanzado se pueden ajustar los parámetros disponibles de generación. Por defecto se permite terminar al modelo mediante **EOS**, respetando el límite de seguridad del motor (9 000 tokens semánticos, aproximadamente seis minutos como máximo teórico).

Al crear una canción, descarga también su `*.semantic.json` si deseas continuarla después.

### Cover / Remix de FL Studio

1. Abrir **Cover / Remix** y subir el WAV o MP3.
2. Escribir la letra que deberá interpretar el modelo.
3. Elegir **Cover** o **Remix** y describir el nuevo estilo.
4. Pulsar **Crear cover / remix automáticamente**.

**MIDI y partitura ABC son opcionales.** Están en la sección avanzada para mejorar la conservación de la melodía. Si se dispone del MIDI de la línea vocal o de la melodía principal de FL Studio, conviene usarlo.

> El extractor automático estima la melodía de un fragmento de la mezcla (aproximadamente 24 segundos). En música con varios instrumentos simultáneos puede identificar notas que no pertenecen a la voz. **No preserva la interpretación vocal exacta**.

### Extender una demo de FL Studio

1. Abrir **Extender FL Studio** y subir un WAV/MP3.
2. Indicar cómo debería continuar la composición y escribir la nueva letra.
3. Elegir duración aproximada y longitud del **crossfade**.
4. Pulsar **Extender y unir audio**.

El sistema toma una referencia de los últimos compases, genera una nueva interpretación y la une al archivo original. **No es una continuación acústica directa:** la transición puede revelar cambios de instrumentos, timbre, armonía o voz.

### Continuar una canción hecha con YuE2

1. En una generación previa de YuE2, conservar el archivo `*.semantic.json`.
2. Abrir **Continuar una canción YuE2**.
3. Subir el JSON, indicar estilo, letra y segundos nuevos.
4. Generar y descargar el nuevo WAV y los tokens actualizados.

Esta opción sí utiliza la función nativa `semantic_prefix` del motor. El audio anterior se **vuelve a sintetizar**, de modo que puede variar ligeramente respecto a la primera salida.

## Limitaciones conocidas

- **Covers:** desde un audio mezclado no se conserva necesariamente la melodía exacta; la voz y la manera de cantar se regeneran.
- **Remixes:** no hay edición de pistas por instrumento, separación de stems ni sustitución fiel de instrumentos en una grabación.
- **Extensión externa:** se genera otra sección y se une al WAV; no existe codificación WAV → `semantic_prefix` en este proyecto.
- **Duración:** los límites en tokens son aproximados y una canción puede terminar antes por EOS.
- **Idiomas:** el rendimiento vocal en español y otros idiomas puede variar; no se garantiza la pronunciación.
- **Entorno:** optimizado y probado para Linux CUDA/Tesla T4; no se garantiza funcionamiento en hardware distinto.
- **Concurrencia:** el panel serializa generaciones para proteger los recursos del servidor.
- **Uso comercial:** los pesos YuE2 están sujetos a una licencia no comercial.

## Estructura del repositorio

```text
yue2-music-lab/
├── app.py                 # Base de validación e interfaz clásica
├── studio_fl.py           # Interfaz principal: cuatro pestañas
├── flstudio_tools.py      # Análisis WAV/MP3, MIDI/ABC y crossfade
├── requirements.txt       # Dependencias Python
├── .env.example           # Variables de entorno de referencia
├── .gitignore             # Excluye pesos, audio, binarios y secretos
├── CHANGELOG.md           # Historial de versiones
├── kaggle/
│   └── YuE2_Music_Lab_ThowiLabs.ipynb # Notebook de instalación desde GitHub
├── scripts/
│   ├── install.py         # Instalación verificando precompilado y pesos
│   ├── run.py             # Inicio de API CUDA y Gradio
│   ├── package.py         # Paquete ZIP de código e historial
│   ├── smoke.py           # Prueba mínima GPU
│   ├── smoke_fl.py        # Prueba de ABC externo
│   ├── smoke_cover_auto.py# WAV -> cover automático
│   └── smoke_continue_fl.py # Continuación semántica
├── tests/                 # Pruebas de parámetros y flujos FL Studio
├── contexto/              # Historial técnico y decisiones
├── tareas/                # Registro de implementación
├── models/                # Pesos locales (ignorados por Git)
├── engine/                # Motor y binarios (ignorados por Git)
├── outputs/               # Canciones y archivos generados (ignorados)
└── logs/                  # Registros de ejecución (ignorados)
```

## Pruebas

Ejecutar las pruebas de lógica e interfaz:

```bash
python -m unittest discover -s tests -v
```

Con una API CUDA ya funcionando en el puerto 7876 se pueden realizar pruebas reales:

```bash
python scripts/smoke.py
python scripts/smoke_fl.py
python scripts/smoke_cover_auto.py
python scripts/smoke_continue_fl.py
```

**Validación realizada en el entorno de desarrollo:** 18 pruebas automáticas correctas, un cover sintetizado desde una referencia WAV analizada automáticamente y una continuación de 220 a 440 tokens semánticos. Los resultados son funcionales, no una garantía de fidelidad musical para canciones externas.

Comprobar el servidor:

```bash
curl -fsS http://127.0.0.1:7876/health
curl -fsS http://127.0.0.1:7876/v1/models
```

## Problemas comunes

| Problema | Posible solución |
| --- | --- |
| No se detecta la GPU | Verificar NVIDIA/CUDA 12.8 y rutas del driver; revisar `logs/backend.log` |
| Faltan archivos GGUF | Repetir `python scripts/install.py` |
| Puerto 7875 o 7876 ocupado | Detener la instancia propia o configurar puertos distintos |
| El cover cambia la voz | Es una limitación del método de transcripción y regeneración; no la corrige aumentar NAR |
| Melodía del cover incorrecta | Aportar MIDI de la melodía principal o revisar ABC en ajustes opcionales |
| Extensión con salto audible | Ajustar crossfade; el sistema no garantiza continuidad exacta |
| La URL pública deja de funcionar | Los túneles Gradio Share son temporales; iniciar una sesión nueva |
| Generación terminada antes de tiempo | Revisar duración en tokens, letra, muestreo y límite EOS |

## Licencias y créditos

- **YuE2-3B y conversión GGUF:** [audio-cpp/Yue2-3B-GGUF](https://huggingface.co/audio-cpp/Yue2-3B-GGUF) y [m-a-p/YuE2-3B](https://huggingface.co/m-a-p/YuE2-3B). Pesos publicados bajo **Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)**. Consulta las condiciones antes de utilizarlos o distribuir resultados comercialmente.
- **Motor de inferencia:** [audio.cpp](https://github.com/0xShug0/audio.cpp), con su licencia **Apache-2.0**.
- **Interfaz y procesamiento:** [Gradio](https://www.gradio.app/), [librosa](https://librosa.org/), [music21](https://web.mit.edu/music21/) y [FFmpeg](https://ffmpeg.org/), cada uno bajo sus respectivas licencias.

**El código propio de este repositorio aún no tiene una licencia de distribución explícita.** Publicarlo en GitHub no otorga automáticamente permiso para reutilizarlo. El propietario puede añadir un archivo `LICENSE` para determinar sus condiciones.

Este proyecto es independiente y no está afiliado oficialmente a YuE2, audio.cpp, FL Studio ni Suno.

---

**Mantenido por [ThowiLabs](https://github.com/thowilabs).** Los problemas reproducibles y propuestas de mejora pueden registrarse como *issues* una vez publicado el repositorio.
