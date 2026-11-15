"""Exercita regras de qualidade ausentes no recorte real de 4.000 linhas."""

import sys
import tempfile
import unittest
from pathlib import Path

from botocore.exceptions import ClientError
from pyspark.sql import SparkSession

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from build_sprint2 import OUTPUTS, deduplicate, normalize, publish  # noqa: E402
from ingest_bronze import FIELDS  # noqa: E402


class Sprint2RulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spark = SparkSession.builder.master("local[1]").appName("sprint2-rules-test").getOrCreate()
        cls.spark.sparkContext.setLogLevel("ERROR")

    @classmethod
    def tearDownClass(cls):
        cls.spark.stop()

    def test_normalization_deduplication_and_rejection(self):
        baseline = {field: "" for field in FIELDS}
        baseline.update({"subject": "  Login  ", "body": "Help", "type": " INCIDENT ", "priority": " HIGH ", "language": " EN ", "queue": " Service "})
        duplicate = dict(baseline, subject="Login", type="incident", priority="high", language="en", queue="Service")
        rejected = dict(baseline, subject=" ", body="", answer="different answer")
        frame = self.spark.createDataFrame([baseline, duplicate, rejected]).select(*FIELDS)
        silver = deduplicate(normalize(frame))
        rows = {row.quality_status: row for row in silver.collect()}
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows["valid"].type, "incident")
        self.assertEqual(rows["valid"].priority, "high")
        self.assertEqual(rows["valid"].language, "en")
        self.assertEqual(rows["rejected"].subject, "")
        self.assertTrue(rows["rejected"].body_missing)


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.put_calls = 0

    def head_object(self, Bucket, Key, ChecksumMode, ExpectedBucketOwner):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return self.objects[Key]

    def put_object(self, Bucket, Key, Body, IfNoneMatch, ExpectedBucketOwner, ChecksumSHA256, ServerSideEncryption, Metadata, ContentType):
        self.put_calls += 1
        self.objects[Key] = {"ChecksumSHA256": ChecksumSHA256, "Metadata": Metadata}


class PublishTest(unittest.TestCase):
    def test_reexecution_reuses_objects_and_detects_changed_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for name in OUTPUTS:
                target = output / name
                target.mkdir()
                (target / "part.parquet").write_bytes(name.encode())
            (output / "quality.json").write_text('{"source_rows":4000}\n', encoding="utf-8")
            s3 = FakeS3()
            publish(s3, "test-bucket", output, "123456789012")
            publish(s3, "test-bucket", output, "123456789012")
            self.assertEqual(s3.put_calls, 4)
            (output / "quality.json").write_text('{"source_rows":3999}\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Métricas existentes divergem"):
                publish(s3, "test-bucket", output, "123456789012")


if __name__ == "__main__":
    unittest.main()
