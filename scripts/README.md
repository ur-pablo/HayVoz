# Scripts

El instalador automatizado está en [`../install.sh`](../install.sh). Mantiene las
acciones sensibles explícitas: no instala el servicio de usuario salvo con
`--with-service`, no descarga modelos salvo con `--with-model`, y nunca solicita
credenciales en argumentos de línea de comandos.

Este directorio queda reservado para futuras herramientas de mantenimiento que
cumplan las mismas garantías de privacidad.
