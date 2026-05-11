from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Sequence, TextIO

from idp_synthetic_config.cli import main as synthetic_config_main
from idp_synthetic_config.generator import GeneratorOptions, generate_synthetic_config
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
            return _handle_seed_config(args)
        if args.command == "start":
            seed_exit = _handle_seed_config(args)
            if seed_exit != 0:
                return seed_exit
            return asyncio.run(_handle_run(args, out))
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
    run.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help="Stop after this duration; run until interrupted when omitted.",
    )

    seed = subparsers.add_parser(
        "seed-config",
        help="Delegate synthetic config seeding to idp-synthetic-config",
    )
    _add_common_args(seed)
    seed.add_argument("--config-registry-url", default="http://localhost:8000")
    seed.add_argument("--no-reset", action="store_true")
    seed.add_argument("--allow-destructive-reset", action="store_true")

    start = subparsers.add_parser("start", help="Seed config, then run emulator")
    _add_common_args(start)
    start.add_argument("--config-registry-url", default="http://localhost:8000")
    start.add_argument("--no-reset", action="store_true")
    start.add_argument("--allow-destructive-reset", action="store_true")
    start.add_argument("--duration-seconds", type=float, default=None)

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
    model = generate_synthetic_config(_options(args))
    plan = build_emulator_plan(
        model,
        host=args.host,
        port=args.port,
        source_id=args.source_id,
        interval_seconds=args.interval_seconds,
    )
    server = KnxSourceEmulatorServer(plan, seed=args.seed)
    if args.duration_seconds is None:
        async with server:
            await asyncio.Event().wait()
    else:
        await server.serve_for(args.duration_seconds)
    payload = server.stats.to_dict()
    if server._server is not None and server._server.sockets:
        host, port = server.bound_address
        payload.update({"host": host, "port": port})
    json.dump(payload, stdout, ensure_ascii=False, indent=2)
    stdout.write("\n")
    return 0


def _handle_seed_config(args: argparse.Namespace) -> int:
    seed_args = [
        "seed",
        "--devices",
        str(args.devices),
        "--tags-per-device",
        str(args.tags_per_device),
        "--source-id",
        args.source_id,
        "--seed",
        str(args.seed),
        "--config-registry-url",
        args.config_registry_url,
    ]
    if args.no_reset:
        seed_args.append("--no-reset")
    if args.allow_destructive_reset:
        seed_args.append("--allow-destructive-reset")
    return synthetic_config_main(seed_args)


def _options(args: argparse.Namespace) -> GeneratorOptions:
    return GeneratorOptions(
        devices=args.devices,
        tags_per_device=args.tags_per_device,
        source_id=args.source_id,
        seed=args.seed,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
