# Configuration

Precedence is process environment, private `config.env`, then defaults. Select a
non-default file with `HAYVOZ_CONFIG_FILE`.

Default config paths:

- macOS: `~/Library/Application Support/HayVoz/config.env`
- Windows: `%APPDATA%\HayVoz\config.env`
- Linux: `${XDG_CONFIG_HOME:-~/.config}/hayvoz/config.env`

Copy `.env.example`, add only the values you need, and restrict the file to the
current user (`chmod 600` on macOS/Linux). The parser supports `KEY=value`, quoted
values, comments, and optional `export`; it does not execute shell expressions.

The local Core needs no AI variables. The optional OpenAI integration uses the
`HAYVOZ_AI_*` contract. Environment variables override file values, allowing
secret managers and service environments without changing disk configuration.
Secrets are marked non-representable and are never persisted. Install the
optional SDK only when needed with `pip install "hayvoz[openai]"`.

`HAYVOZ_DATA_DIR` selects the private data root. Changing it does not move old
data automatically; move the directory while HayVoz is stopped, then update the
setting.
