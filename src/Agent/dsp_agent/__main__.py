"""Inspect the local bridge bootstrap endpoint."""

import argparse
import json
import sys
from .client import BridgeError, read_health


def main():
    parser = argparse.ArgumentParser(description="DSP bridge bootstrap inspection")
    parser.add_argument("--bridge", default="http://127.0.0.1:38741")
    args = parser.parse_args()
    try:
        result = read_health(args.bridge)
    except BridgeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
