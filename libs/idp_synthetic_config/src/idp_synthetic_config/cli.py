from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, TextIO

from idp_synthetic_config.config_registry_seeder import (
    ConfigRegistryError,
    ConfigRegistryHttpClient,
    ConfigRegistrySeeder,
)
from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from idp_synthetic_config.reset import DestructiveResetRefused, ResetPolicy


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = _parser()
    args = parser.parse_args(argv)
    options = _generator_options(args)
    model = generate_synthetic_config(options)

    if args.command == "plan":
        _write_document(model.to_plan_dict(), args.format, out)
        return 0

    if args.command == "seed":
        config_registry_url = args.config_registry_url
        reset_policy = ResetPolicy(
            enabled=not args.no_reset,
            allow_destructive_reset=args.allow_destructive_reset,
            clickhouse_url=args.clickhouse_url,
            mqtt_broker_url=args.mqtt_broker_url,
        )
        client = ConfigRegistryHttpClient(
            config_registry_url,
            timeout_seconds=args.timeout_seconds,
        )
        seeder = ConfigRegistrySeeder(client, reset_policy=reset_policy)
        try:
            issued_at = _parse_issued_at(args.issued_at)
            summary = seeder.seed(
                model,
                config_registry_url=config_registry_url,
                config_revision=args.config_revision,
                issued_at=issued_at,
            )
        except (ConfigRegistryError, DestructiveResetRefused, ValueError) as exc:
            print(str(exc), file=err)
            return 2
        _write_document(summary.to_dict(), args.format, out)
        return 0 if summary.ok else 1

    if args.command == "delete":
        config_registry_url = args.config_registry_url
        reset_policy = ResetPolicy(
            enabled=True,
            allow_destructive_reset=args.allow_destructive_reset,
        )
        client = ConfigRegistryHttpClient(
            config_registry_url,
            timeout_seconds=args.timeout_seconds,
        )
        seeder = ConfigRegistrySeeder(client, reset_policy=reset_policy)
        try:
            summary = seeder.delete_generated(
                model,
                config_registry_url=config_registry_url,
            )
        except (ConfigRegistryError, DestructiveResetRefused, ValueError) as exc:
            print(str(exc), file=err)
            return 2
        _write_document(summary.to_dict(), args.format, out)
        return 0 if summary.ok else 1

    parser.error(f"unknown command {args.command!r}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="idp-synthetic-config")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Print generated model without side effects")
    _add_generator_args(plan)
    _add_format_arg(plan)

    seed = subparsers.add_parser("seed", help="Seed generated model into Config Registry")
    _add_generator_args(seed)
    _add_format_arg(seed)
    seed.add_argument(
        "--config-registry-url",
        default=os.getenv("CONFIG_REGISTRY_URL", "http://localhost:8000"),
        help="Config Registry base URL.",
    )
    seed.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP request timeout for Config Registry API.",
    )
    seed.add_argument("--config-revision", default=None)
    seed.add_argument("--issued-at", default=None)
    seed.add_argument("--no-reset", action="store_true")
    seed.add_argument("--allow-destructive-reset", action="store_true")
    seed.add_argument("--clickhouse-url", default=os.getenv("CLICKHOUSE_HTTP_URL"))
    seed.add_argument("--mqtt-broker-url", default=os.getenv("MQTT_BROKER"))

    delete = subparsers.add_parser(
        "delete",
        help="Delete generated model from Config Registry",
    )
    _add_generator_args(delete)
    _add_format_arg(delete)
    delete.add_argument(
        "--config-registry-url",
        default=os.getenv("CONFIG_REGISTRY_URL", "http://localhost:8000"),
        help="Config Registry base URL.",
    )
    delete.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP request timeout for Config Registry API.",
    )
    delete.add_argument("--allow-destructive-reset", action="store_true")
    return parser


def _add_generator_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--devices", type=int, default=GeneratorOptions.devices)
    parser.add_argument(
        "--tags-per-device",
        type=int,
        default=GeneratorOptions.tags_per_device,
    )
    parser.add_argument("--tenant-id", default=GeneratorOptions.tenant_id)
    parser.add_argument("--asset-id", default=GeneratorOptions.asset_id)
    parser.add_argument("--agent-id", default=GeneratorOptions.agent_id)
    parser.add_argument("--source-id", default=GeneratorOptions.source_id)
    parser.add_argument("--seed", type=int, default=GeneratorOptions.seed)


def _add_format_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("json", "yaml"),
        default="json",
        help="Output format.",
    )


def _generator_options(args: argparse.Namespace) -> GeneratorOptions:
    return GeneratorOptions(
        devices=args.devices,
        tags_per_device=args.tags_per_device,
        tenant_id=args.tenant_id,
        asset_id=args.asset_id,
        agent_id=args.agent_id,
        source_id=args.source_id,
        seed=args.seed,
    )


def _parse_issued_at(value: str | None) -> datetime | str | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value


def _write_document(value: Any, output_format: str, stdout: TextIO) -> None:
    if output_format == "json":
        json.dump(value, stdout, ensure_ascii=False, indent=2)
        stdout.write("\n")
        return
    stdout.write(_to_yaml(value))


def _to_yaml(value: Any, *, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, dict | list):
                lines.append(f"{prefix}{key}:")
                lines.append(_to_yaml(item, indent=indent + 2).rstrip())
            else:
                lines.append(f"{prefix}{key}: {_scalar_yaml(item)}")
        return "\n".join(lines) + "\n"
    if isinstance(value, list):
        if not value:
            return f"{prefix}[]\n"
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(_to_yaml(item, indent=indent + 2).rstrip())
            elif isinstance(item, list):
                lines.append(f"{prefix}-")
                lines.append(_to_yaml(item, indent=indent + 2).rstrip())
            else:
                lines.append(f"{prefix}- {_scalar_yaml(item)}")
        return "\n".join(lines) + "\n"
    return f"{prefix}{_scalar_yaml(value)}\n"


def _scalar_yaml(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_.%|/-]+", text):
        return text
    return json.dumps(text, ensure_ascii=False)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
