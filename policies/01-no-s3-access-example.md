# 01 - No S3 Access Example

This scenario is used after the EC2 role exists but before any S3 permissions are attached.

## Expected behavior

- STS identity lookup should succeed
- S3 bucket listing should fail
- UI banner should show:

> DO NOT HAVE ACCESS TO LIST THE BUCKET

## Teaching point

An AWS identity can exist and still be unable to do anything useful in S3 until explicit permissions are granted.

## Suggested setup

- Attach the EC2 trust policy role to the instance
- Do not attach any S3 permissions yet