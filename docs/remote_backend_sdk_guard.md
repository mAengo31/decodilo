# Remote Backend SDK Guard

The SDK guard prevents accidental remote backend implementation before policy
allows it.

It scans for forbidden dependencies and imports:

- boto3 / botocore
- google-cloud-storage / google.cloud
- azure-storage-blob / azure.storage
- s3fs, gcsfs, adlfs, minio
- remote fsspec-style backend usage

It also detects cloud credential environment reads such as `AWS_*`,
`GOOGLE_*`, `AZURE_*`, `LAMBDA_*`, `S3_*`, and `GCS_*`.

Review artifacts are scanned for raw secret-like fields. The guard is evidence
only; passing it does not enable SDK addition.
