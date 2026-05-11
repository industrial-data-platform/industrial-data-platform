from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from idp_config_registry import __main__ as cli


def test_serve_enables_uvicorn_reload_for_package_source(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        cli.ConfigRegistrySettings,
        "from_env",
        staticmethod(lambda: SimpleNamespace(host="127.0.0.1", port=18000)),
    )
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda app, **kwargs: captured.update({"app": app, **kwargs}),
    )

    cli._serve(reload=True)

    assert captured["app"] == "idp_config_registry.main:create_app"
    assert captured["factory"] is True
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 18000
    assert captured["reload"] is True
    assert captured["reload_dirs"] == [
        str(Path(cli.__file__).resolve().parents[1])
    ]
