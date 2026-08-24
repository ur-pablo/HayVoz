# Scripts

El instalador automatizado está en [`../install.sh`](../install.sh). Mantiene las
acciones sensibles explícitas: no instala el servicio de usuario salvo con
`--with-service` o `--with-browser`, no descarga modelos salvo con `--with-model`,
y nunca solicita credenciales en argumentos de línea de comandos. El
desinstalador seguro está en [`../uninstall.sh`](../uninstall.sh) y siempre
conserva los datos privados.

- `package-safari-extension.sh` genera en `build/safari` un proyecto Xcode para
  la WebExtension compartida e inyecta el handler/App Group locales. Requiere
  macOS y un Xcode actual; no firma, instala ni publica la extensión.
- `configure-safari-project.py` aplica el puente nativo y los entitlements al
  proyecto generado por Xcode.
