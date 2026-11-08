"""Obtém um arquivo versionado do Kaggle sem alterar seus bytes."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import kagglehub


HANDLE = "tobiasbueck/multilingual-customer-support-tickets/versions/14"
FILENAME = "dataset-tickets-multi-lang3-4k.csv"
EXPECTED_SHA256 = "9aae7120cf459fc27561febe29c7757c6d222bfebff50e8baa868991e57b87d1"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source = args.output_dir / FILENAME
    if not source.is_file():
        downloaded = Path(kagglehub.dataset_download(HANDLE, path=FILENAME, output_dir=str(args.output_dir)))
        source = downloaded if downloaded.is_file() else downloaded / FILENAME
    if not source.is_file():
        raise FileNotFoundError(f"Arquivo esperado ausente: {source}")
    with source.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"SHA-256 inesperado: {digest}; esperado: {EXPECTED_SHA256}")
    print(f"Arquivo: {source}\nBytes: {source.stat().st_size}\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
