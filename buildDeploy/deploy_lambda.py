#!/usr/bin/env python3
"""
Deploy a Lambda function zip to AWS.

Reads settings from deploy_config.json (sitting next to this script),
uses AWS SSO credentials via a named profile, and updates the Lambda
function code.

Usage
-----
    python deploy_lambda.py              # build + deploy
    python deploy_lambda.py --skip-build # deploy only (zip must already exist)
    python deploy_lambda.py --config /path/to/other_config.json

To reuse in another repo, copy the buildDeploy/ folder, edit
deploy_config.json with your own values, and you're good to go.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import boto3


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        cfg = json.load(f)

    required_keys = [
        "aws_profile",
        "aws_region",
        "lambda_function_name",
        "zip_path",
        "build_script",
    ]
    missing = [k for k in required_keys if k not in cfg]
    if missing:
        sys.exit(f"deploy_config.json is missing keys: {', '.join(missing)}")

    return cfg


def run_build(build_script: str, script_dir: Path) -> None:
    script = script_dir / build_script
    if not script.exists():
        sys.exit(f"Build script not found: {script}")

    print(f"\n--- Running build: {script} ---\n")
    result = subprocess.run(
        ["bash", str(script)],
        cwd=str(script_dir),
    )
    if result.returncode != 0:
        sys.exit(f"Build failed (exit {result.returncode})")


def deploy(cfg: dict, script_dir: Path) -> None:
    zip_path = (script_dir / cfg["zip_path"]).resolve()
    if not zip_path.exists():
        sys.exit(f"Zip not found: {zip_path}\nRun the build first or remove --skip-build.")

    zip_bytes = zip_path.read_bytes()
    zip_mb = len(zip_bytes) / (1024 * 1024)
    print(f"\nUploading {zip_path.name} ({zip_mb:.1f} MB) -> {cfg['lambda_function_name']}")

    session = boto3.Session(
        profile_name=cfg["aws_profile"],
        region_name=cfg["aws_region"],
    )
    client = session.client("lambda")

    resp = client.update_function_code(
        FunctionName=cfg["lambda_function_name"],
        ZipFile=zip_bytes,
        Publish=True,
    )

    version = resp.get("Version", "?")
    state = resp.get("State", "?")
    print(f"\nDeployed version {version}  (state: {state})")
    print(f"Function ARN: {resp.get('FunctionArn', 'n/a')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Lambda function to AWS")
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip running the build script (zip must already exist)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to deploy_config.json (default: next to this script)",
    )
    args = parser.parse_args()

    # Resolve paths relative to the script location (not cwd)
    script_dir = Path(__file__).resolve().parent
    config_path = args.config or (script_dir / "deploy_config.json")
    cfg = load_config(config_path)

    if not args.skip_build:
        run_build(cfg["build_script"], script_dir)

    deploy(cfg, script_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
