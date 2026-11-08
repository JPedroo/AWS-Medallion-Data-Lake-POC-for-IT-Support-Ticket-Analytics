"""Checkpoint local mínimo de PySpark; não lê dados de negócio."""

from pyspark.sql import SparkSession


spark = SparkSession.builder.master("local[2]").appName("medallion-sprint1-check").getOrCreate()
try:
    assert spark.range(5).count() == 5
    print(f"Spark local validado: {spark.version}; registros=5")
finally:
    spark.stop()
