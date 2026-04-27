#!/usr/bin/env python3
"""
Upload all auth/*.json session files to the HuggingFace Space repo so
Playwright tests can find them at /app/auth/ inside the container.

Usage:
    python scripts/upload_auth_to_hf.py [--token HF_TOKEN] [--repo REPO_ID]

Requires:
    pip install huggingface_hub
"""

import argparse
import os
import sys
from pathlib import Path

HF_REPO_ID   = "sarimsikander/zambeel-sqa"
HF_REPO_TYPE = "space"
AUTH_DIR     = Path(__file__).resolve().parent.parent / "auth"


def main():
    parser = argparse.ArgumentParser(description="Upload auth sessions to HuggingFace Space")
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"), help="HuggingFace API token")
    parser.add_argument("--repo",  default=HF_REPO_ID, help=f"HF repo ID (default: {HF_REPO_ID})")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: HuggingFace token required. Set HF_TOKEN env var or pass --token.")
        sys.exit(1)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    json_files = sorted(AUTH_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {AUTH_DIR}")
        sys.exit(0)

    api = HfApi(token=args.token)
    print(f"Uploading {len(json_files)} auth file(s) to {args.repo} ...")

    for path in json_files:
        dest = f"auth/{path.name}"
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=dest,
            repo_id=args.repo,
            repo_type=HF_REPO_TYPE,
        )
        print(f"  uploaded {path.name} -> {dest}")

    print(f"\nDone. Trigger a rebuild of the Space so the new auth files are included.")


if __name__ == "__main__":
    main()
