from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import replace
from typing import Sequence, TextIO

from idp_synthetic_config.config_registry_seeder import (
    ConfigRegistryHttpClient,
    ConfigRegistrySeeder,
    SeedSummary,
)
from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
from idp_synthetic_config.models import SyntheticModel
from idp_synthetic_config.reset import ResetPolicy
from knx_source_emulator.plan import build_emulator_plan
from knx_source_emulator.server import KnxSourceEmulatorServer


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    try:
        if args.command == "plan":
            return _handle_plan(args, out)
        if args.command == "run":
            return asyncio.run(_handle_run(args, out))
        if args.command == "seed-config":
            return _handle_seed_config(args, out)
        if args.command == "start":
            return asyncio.run(_handle_start(args, out))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=err)
        return 1
    parser.error(f"unknown command {args.command!r}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="knx-source-emulator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan", help="Show future emulator device plan")
    _add_common_args(plan)
    plan.add_argument("--dry-run", action="store_true", help="Show plan without side effects")
    plan.add_argument("--format", choices=("json",), default="json")

    run = subparsers.add_parser("run", help="Run TCP device emulator")
    _add_common_args(run)
    _add_runtime_args(run)

    seed = subparsers.add_parser(
        "seed-config",
        help="Delegate synthetic config seeding to idp-synthetic-config",
    )
    _add_common_args(seed)
    seed.add_argument("--config-registry-url", default="http://localhost:8000")
    seed.add_argument("--no-reset", action="store_true")
    seed.add_argument("--allow-destructive-reset", action="store_true")
    seed.add_argument("--config-revision", default=None)
    seed.add_argument("--issued-at", default=None)
    seed.add_argument("--timeout-seconds", type=float, default=30.0)

    start = subparsers.add_parser("start", help="Seed config, then run emulator")
    _add_common_args(start)
    start.add_argument("--config-registry-url", default="http://localhost:8000")
    start.add_argument("--no-reset", action="store_true")
    start.add_argument("--allow-destructive-reset", action="store_true")
    start.add_argument("--config-revision", default=None)
    start.add_argument("--issued-at", default=None)
    start.add_argument("--timeout-seconds", type=float, default=30.0)
    _add_runtime_args(start)

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3671)
    parser.add_argument("--devices", type=int, default=GeneratorOptions.devices)
    parser.add_argument(
        "--tags-per-device",
        type=int,
        default=GeneratorOptions.tags_per_device,
    )
    parser.add_argument("--source-id", default=GeneratorOptions.source_id)
    parser.add_argument("--seed", type=int, default=GeneratorOptions.seed)
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=None,
        help="Fast local emission interval override; plan output keeps generated point settings.",
    )
    parser.add_argument("--log-level", default="INFO")


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help="Stop after this duration; run until interrupted when omitted.",
    )
    parser.add_argument(
        "--forever",
        action="store_true",
        help="Run until interrupted; explicit form of omitting --duration-seconds.",
    )


def _handle_plan(args: argparse.Namespace, stdout: TextIO) -> int:
    del args.dry_run
    model = generate_synthetic_config(_options(args))
    plan = build_emulator_plan(
        model,
        host=args.host,
        port=args.port,
        source_id=args.source_id,
        interval_seconds=args.interval_seconds,
    )
    json.dump(plan.to_dict(), stdout, ensure_ascii=False, indent=2)
    stdout.write("\n")
    return 0


async def _handle_run(args: argparse.Namespace, stdout: TextIO) -> int:
    duration_seconds = _runtime_duration_seconds(args)
    model = generate_synthetic_config(_options(args))
    plan = build_emulator_plan(
        model,
        host=args.host,
        port=args.port,
        source_id=args.source_id,
        interval_seconds=args.interval_seconds,
    )
    server = KnxSourceEmulatorServer(plan, seed=args.seed)
    async with server:
        host, port = server.bound_address
        await _wait_for_runtime_duration(duration_seconds)
    payload = server.stats.to_dict()
    payload.update({"host": host, "port": port})
    json.dump(payload, stdout, ensure_ascii=False, indent=2)
    stdout.write("\n")
    return 0


def _handle_seed_config(args: argparse.Namespace, stdout: TextIO) -> int:
    if args.port == 0:
        raise ValueError("seed-config requires a concrete --port; use start with --port 0")
    model = _model_with_endpoint(
        generate_synthetic_config(_options(args)),
        host=args.host,
        port=args.port,
    )
    summary = _seed_model(args, model)
    _write_summary(summary, stdout)
    return 0 if summary.ok else 1


async def _handle_start(args: argparse.Namespace, stdout: TextIO) -> int:
    duration_seconds = _runtime_duration_seconds(args)
    model = generate_synthetic_config(_options(args))
    plan = build_emulator_plan(
        model,
        host=args.host,
        port=args.port,
        source_id=args.source_id,
        interval_seconds=args.interval_seconds,
    )
    server = KnxSourceEmulatorServer(plan, seed=args.seed)
    async with server:
        host, port = server.bound_address
        summary = _seed_model(
            args,
            _model_with_endpoint(model, host=host, port=port),
        )
        if not summary.ok:
            _write_summary(summary, stdout)
            return 1
        await _wait_for_runtime_duration(duration_seconds)
    payload = server.stats.to_dict()
    payload.update(
        {
            "host": host,
            "port": port,
            "seed_config": summary.to_dict(),
        }
    )
    json.dump(payload, stdout, ensure_ascii=False, indent=2)
    stdout.write("\n")
    return 0


def _options(args: argparse.Namespace) -> GeneratorOptions:
    return GeneratorOptions(
        devices=args.devices,
        tags_per_device=args.tags_per_device,
        source_id=args.source_id,
        seed=args.seed,
    )


def _runtime_duration_seconds(args: argparse.Namespace) -> float | None:
    if args.forever and args.duration_seconds is not None:
        raise ValueError("--forever cannot be combined with --duration-seconds")
    return args.duration_seconds


async def _wait_for_runtime_duration(duration_seconds: float | None) -> None:
    if duration_seconds is None:
        await asyncio.Event().wait()
    else:
        await asyncio.sleep(duration_seconds)


def _model_with_endpoint(model: SyntheticModel, *, host: str, port: int) -> SyntheticModel:
    if port == 0:
        raise ValueError("source config endpoint port must be bound before seeding")
    source = model.sources[0]
    updated_source = replace(
        source,
        connection_json={
            **source.connection_json,
            "mode": "synthetic",
            "host": host,
            "port": port,
            "gateway_ip": host,
            "gateway_port": port,
        },
    )
    return replace(model, sources=(updated_source,))


def _seed_model(args: argparse.Namespace, model: SyntheticModel) -> SeedSummary:
    reset_policy = ResetPolicy(
        enabled=not args.no_reset,
        allow_destructive_reset=args.allow_destructive_reset,
    )
    seeder = ConfigRegistrySeeder(
        ConfigRegistryHttpClient(
            args.config_registry_url,
            timeout_seconds=args.timeout_seconds,
        ),
        reset_policy=reset_policy,
    )
    return seeder.seed(
        model,
        config_registry_url=args.config_registry_url,
        config_revision=args.config_revision,
        issued_at=args.issued_at,
    )


def _write_summary(summary: SeedSummary, stdout: TextIO) -> None:
    json.dump(summary.to_dict(), stdout, ensure_ascii=False, indent=2)
    stdout.write("\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
