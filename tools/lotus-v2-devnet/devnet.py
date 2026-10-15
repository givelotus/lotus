#!/usr/bin/env python3
"""Run a foreground, explicitly configured private Lotus V2 testnet playground."""
import argparse
import getpass
import hmac
import json
from pathlib import Path
import signal
import sys

from controller import Controller, ControllerError, SigningInterrupted, load_config


def terminal_secret(name, operation):
    # getpass restores echo on interruption. Python/terminal copies are not a
    # secure-memory guarantee; the bounded mutable transport buffer is cleared.
    if not sys.stdin.isatty():
        raise ControllerError(
            "invalid", "secret operations require an interactive terminal"
        )
    secret = bytearray(getpass.getpass(f"{name} passphrase: ").encode("utf8"))
    try:
        if operation == "create":
            confirmation = bytearray(
                getpass.getpass("Repeat passphrase: ").encode("utf8")
            )
            try:
                if not hmac.compare_digest(secret, confirmation):
                    raise ControllerError("invalid", "passphrases differ")
            finally:
                confirmation[:] = b"\0" * len(confirmation)
        if not 0 < len(secret) <= 4096:
            raise ControllerError("invalid", "passphrase must encode to 1..4096 bytes")
        return secret
    except BaseException:
        secret[:] = b"\0" * len(secret)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--session",
        type=Path,
        required=True,
        help="new directory; existing homes are never reused",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate pins/configuration only; no processes or files",
    )
    args = parser.parse_args(argv)
    controller = None
    previous = {}
    try:
        config = load_config(args.config)
        if args.check:
            print(json.dumps({"ok": True, "result": "configuration_checked"}))
            return 0
        controller = Controller(config, args.session, terminal_secret)

        def interrupted(signum, _frame):
            raise KeyboardInterrupt

        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, interrupted)
        controller.start()
        print(
            json.dumps(
                {
                    "ok": True,
                    "result": "started",
                    "session": str(controller.session),
                    "nodes": list(controller.nodes),
                }
            ),
            flush=True,
        )
        while not controller.closed:
            try:
                if sys.stdin.isatty():
                    print("devnet> ", end="", flush=True)
                line = sys.stdin.readline(config["limits"]["max_line_bytes"] + 1)
                if not line:
                    break
                if len(line.encode("utf8")) > config["limits"]["max_line_bytes"]:
                    raise ControllerError(
                        "capacity_refused", "controller command line exceeds cap"
                    )
            except EOFError:
                break
            if not line.strip():
                continue
            print(
                json.dumps(controller.execute(line), separators=(",", ":")), flush=True
            )
        return 0
    except SigningInterrupted as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "result": "outcome_unknown",
                    "error": "sign interrupted; use wallet pending/export before retrying",
                    "recovery_note": getattr(error, "recovery_note", None),
                }
            ),
            flush=True,
        )
        return 130
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "result": "interrupted"}), flush=True)
        return 130
    except (ControllerError, OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "result": getattr(error, "code", "setup_error"),
                    "error": str(error),
                }
            ),
            flush=True,
        )
        return 1
    finally:
        if controller:
            controller.close()
            if controller.cleanup_errors:
                print(
                    json.dumps(
                        {
                            "ok": False,
                            "result": "cleanup_incomplete",
                            "cleanup_errors": controller.cleanup_errors,
                        }
                    ),
                    flush=True,
                )
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
