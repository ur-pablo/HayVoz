from __future__ import annotations

import os
import stat

from app.config import Settings
from app.local_config import load_local_config


def test_private_config_loads_without_shell_evaluation_and_environment_wins(
    tmp_path, monkeypatch
) -> None:
    config = tmp_path / "private" / "config.env"
    config.parent.mkdir()
    config.write_text(
        "\n".join(
            [
                "HAYVOZ_LANGUAGE=pt_BR",
                f"HAYVOZ_DATA_DIR={tmp_path / 'data'}",
                "HAYVOZ_AUDIO_BACKEND=avfoundation",
                "HAYVOZ_AI_API_KEY=from-file",
                "HAYVOZ_AI_MODEL=test-model",
                "LITERAL=$(this-is-not-executed)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HAYVOZ_CONFIG_FILE", str(config))
    monkeypatch.setenv("HAYVOZ_AI_API_KEY", "from-process")

    settings = Settings.from_env()
    settings.ensure_directories()

    assert settings.language == "pt"
    assert settings.ai_api_key == "from-process"
    assert settings.ai_model == "test-model"
    assert load_local_config(config)["LITERAL"] == "$(this-is-not-executed)"
    assert "from-process" not in repr(settings)
    if os.name != "nt":
        assert stat.S_IMODE(config.stat().st_mode) == 0o600
        assert stat.S_IMODE(settings.data_dir.stat().st_mode) == 0o700


def test_hayvoz_ai_names_precede_openai_compatibility_names(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("HAYVOZ_CONFIG_FILE", str(tmp_path / "missing.env"))
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HAYVOZ_AUDIO_BACKEND", "avfoundation")
    monkeypatch.setenv("HAYVOZ_AI_API_KEY", "hayvoz-key")
    monkeypatch.setenv("OPENAI_API_KEY", "compatibility-key")
    monkeypatch.setenv("HAYVOZ_AI_MODEL", "hayvoz-model")
    monkeypatch.setenv("OPENAI_MODEL", "compatibility-model")

    settings = Settings.from_env()

    assert settings.ai_api_key == "hayvoz-key"
    assert settings.ai_model == "hayvoz-model"


def test_background_runtime_can_discard_ai_credentials(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HAYVOZ_CONFIG_FILE", str(tmp_path / "missing.env"))
    monkeypatch.setenv("HAYVOZ_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("HAYVOZ_AUDIO_BACKEND", "avfoundation")
    monkeypatch.setenv("HAYVOZ_AI_API_KEY", "must-not-remain-in-memory")

    settings = Settings.from_env(load_ai_credentials=False)

    assert settings.ai_api_key is None
