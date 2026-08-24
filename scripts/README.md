# Scripts

El instalador automatizado está en [`../install.sh`](../install.sh). Mantiene las
acciones sensibles explícitas: no instala el servicio de usuario salvo con
`--with-service`, no descarga modelos salvo con `--with-model`, y nunca solicita
credenciales en argumentos de línea de comandos.

- `package-safari-extension.sh` genera en `build/safari` un proyecto Xcode para
  la WebExtension compartida. Requiere macOS y un Xcode actual; no firma, instala
  ni publica la extensión.
