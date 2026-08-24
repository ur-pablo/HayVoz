# Captura separada de audio en macOS

## Decisión para el MVP

La Fase 5 soporta dos fuentes solamente en `record` mode:

- `--device`: micrófono local, guardado como `<session-id>.flac` y etiquetado
  como `interviewer` al transcribir.
- `--system-device`: entrada virtual con el audio remoto/sistema, guardada como
  `<session-id>.system.flac` y etiquetada como `interviewee`.

Ambos archivos son escritos por un único proceso `ffmpeg`. Whisper los procesa
después de la reunión, en serie y con una sola instancia del modelo. Assistant
mantiene por ahora una sola fuente para no añadir un segundo pipeline activo ni
duplicar el consumo durante la reunión.

## Por qué macOS necesita configuración adicional

AVFoundation enumera micrófonos y dispositivos de entrada, pero el audio que
reproducen Chrome, Meet u otras aplicaciones no aparece normalmente como una
entrada grabable. Para convertir esa salida en una entrada se necesita una de
estas alternativas:

1. Un dispositivo virtual de loopback como BlackHole.
2. Un capturador nativo basado en ScreenCaptureKit o Core Audio process taps.

Apple documenta que un dispositivo Multi-Output reproduce simultáneamente por
varios dispositivos. BlackHole actúa como loopback: recibe una copia de esa
salida y la expone como entrada a `ffmpeg`.

Para este MVP se eligió **BlackHole 2ch como dependencia externa opcional**.
Soporta Mac Intel y evita agregar un helper Swift residente. La aplicación no
lo instala, no ejecuta comandos privilegiados y no lo redistribuye. El proyecto
de BlackHole señala además requisitos de licencia para proyectos no GPLv3; por
eso cualquier futura distribución conjunta requiere una revisión separada.

ScreenCaptureKit puede capturar audio si `capturesAudio` está habilitado, pero
integrarlo correctamente exigiría un binario nativo, permisos de captura del
sistema y manejo de compatibilidad de macOS. Es una alternativa futura, no una
dependencia oculta de esta versión.

## Configuración manual con BlackHole 2ch

1. Revisa el proyecto oficial y decide si quieres instalar BlackHole 2ch. La
   instalación modifica componentes de audio del sistema y debe ser iniciada
   por ti.
2. Abre **Configuración de Audio MIDI**.
3. Crea un **Dispositivo de salida múltiple**.
4. Incluye tus altavoces o audífonos y `BlackHole 2ch`.
5. Usa los altavoces o audífonos como dispositivo principal y activa corrección
   de deriva para BlackHole cuando corresponda. Ambos deben usar la misma
   frecuencia de muestreo.
6. Selecciona ese dispositivo de salida múltiple como salida de macOS o de la
   aplicación de reunión.
7. Comprueba los índices sin grabar:

   ```bash
   uv run hayvoz devices
   uv run hayvoz doctor --skip-mic-check
   ```

8. Inicia una sesión indicando índices diferentes:

   ```bash
   uv run hayvoz start \
     --title "Entrevista con dos fuentes" \
     --mode record \
     --device 0 \
     --system-device 1 \
     --local-only
   ```

Si eliges BlackHole directamente como única salida, dejarás de oír el audio.
El dispositivo Multi-Output es el que permite escuchar y capturar a la vez.

## Sincronización y límites

Las dos entradas se abren dentro del mismo proceso, pero pueden usar relojes de
hardware distintos. Sus timestamps empiezan cerca del mismo instante, no con
sincronización de muestra exacta. En reuniones largas puede aparecer deriva si
la configuración de Audio MIDI no aplica corrección.

Un Aggregate Device puede combinar entradas y aplicar una fuente de reloj y
corrección de deriva, como documenta Apple. No se usa automáticamente porque el
orden y número de canales dependen de la configuración local; automatizarlo
sería frágil y requeriría modificar el sistema. Es una opción manual si se
necesita alineación más precisa.

La separación por fuente funciona únicamente si el micrófono local no vuelve a
capturar el sonido de los altavoces. Se recomiendan audífonos para evitar eco y
duplicación de la voz remota.

## Privacidad y fallos

- El audio permanece local y nunca se sube al proveedor de IA.
- `--local-only` también impide enviar la transcripción.
- Si falla una fuente, se conservan todos los archivos que `ffmpeg` haya podido
  cerrar. La sesión no se considera completada si falta uno de los dos audios.
- La transcripción de ambas fuentes termina antes de reemplazar el JSON y los
  segmentos existentes; un fallo de Whisper conserva la versión anterior.

## Referencias oficiales

- [Apple: reproducir audio mediante varios dispositivos](https://support.apple.com/guide/audio-midi-setup/play-audio-through-multiple-devices-at-once-ams7c093f372/mac)
- [Apple: crear un Aggregate Device](https://support.apple.com/en-lamr/102171)
- [BlackHole: repositorio, instalación y compatibilidad](https://github.com/ExistentialAudio/BlackHole)
- [BlackHole: crear un Multi-Output Device](https://github.com/ExistentialAudio/BlackHole/wiki/Getting-Started%3A-Creating-a-Multi-Output-Device)
- [Apple Developer: `SCStreamConfiguration.capturesAudio`](https://developer.apple.com/documentation/screencapturekit/scstreamconfiguration/capturesaudio)
