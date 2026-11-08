"""Contrato da Bronze: bytes preservados, manifesto e reexecução sem overwrite."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import fetch_dataset  # noqa: E402
import ingest_bronze  # noqa: E402


class FakeS3:
    def __init__(self):
        self.objects = {}

    def head_object(self, *, Bucket, Key, **_):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        obj = self.objects[Key]
        return {
            "ContentLength": len(obj["body"]),
            "Metadata": obj.get("Metadata", {}),
            "ChecksumSHA256": obj.get("ChecksumSHA256"),
        }

    def put_object(self, *, Bucket, Key, Body, IfNoneMatch, **kwargs):
        assert IfNoneMatch == "*"
        if Key in self.objects:
            raise ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
        body = Body.read() if hasattr(Body, "read") else Body
        self.objects[Key] = {"body": body, **kwargs}

    def get_object(self, *, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key]["body"])}


class BronzeTest(unittest.TestCase):
    def test_preserves_bytes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / fetch_dataset.FILENAME
            content = (",".join(ingest_bronze.FIELDS) + "\n" +
                       'assunto,"descrição, com vírgula",resposta,Incident,IT Support,high,pt,IT Services,,,,,,,,,\n').encode("utf-8")
            source.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            client = FakeS3()
            fake_session = type("Session", (), {"client": lambda self, _: client})
            args = ["ingest_bronze.py", "--source", str(source), "--bucket", "test-bucket", "--region", "us-east-1"]
            with patch.object(fetch_dataset, "EXPECTED_SHA256", digest), \
                 patch.object(ingest_bronze.boto3, "Session", return_value=fake_session()), \
                 patch.object(sys, "argv", args), contextlib.redirect_stdout(io.StringIO()):
                ingest_bronze.main()
                ingest_bronze.main()
            self.assertEqual(len(client.objects), 2)
            csv_key = next(key for key in client.objects if key.endswith(".csv"))
            manifest_key = next(key for key in client.objects if key.endswith("manifest.json"))
            self.assertEqual(client.objects[csv_key]["body"], content)
            manifest = json.loads(client.objects[manifest_key]["body"])
            self.assertEqual(manifest["source_sha256"], digest)
            self.assertEqual(manifest["source_rows"], 1)


if __name__ == "__main__":
    unittest.main()
