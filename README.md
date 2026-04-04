# IAM Role + S3 Classroom Lab

A lightweight Flask + boto3 demo for teaching how AWS IAM identity and S3 permissions affect application behavior. The app is built for classroom use: it shows clear, visual states for missing credentials, missing permissions, partial success, and full success.

## What this lab teaches

1. No AWS credentials / no EC2 role
2. AWS identity exists but `ListBucket` is denied
3. Bucket listing works but object reads are denied
4. Object reads work but uploads are denied
5. Full success

## Architecture

- **Frontend:** single-page HTML/CSS/JS interface with large classroom-friendly status banners
- **Backend:** Flask app exposing diagnostics, image listing, image proxying, and demo uploads
- **AWS services:**
  - **STS GetCallerIdentity** to confirm the active AWS identity
  - **S3 ListObjectsV2** to test `s3:ListBucket`
  - **S3 GetObject** to test object read access
  - **S3 PutObject** to test upload access

Request flow:

1. Browser loads `/`
2. Frontend calls `/api/diagnostics`
3. Backend evaluates the AWS credential chain and IAM permission stages
4. Frontend displays the correct banner and explanation
5. If read access exists, frontend calls `/api/images` and renders the gallery
6. If upload is attempted, frontend calls `/api/upload-demo-image` then refreshes diagnostics

### Architecture diagram

```text
 ┌──────────────────────┐
 │ Browser / Student UI │
 │  - status banner     │
 │  - diagnostics       │
 │  - gallery           │
 │  - uploads           │
 └──────────┬───────────┘
            │ HTTP
            ▼
 ┌──────────────────────┐
 │ Flask App            │
 │  app.py              │
 │  - /api/diagnostics  │
 │  - /api/images       │
 │  - /api/upload...    │
 └──────────┬───────────┘
            │ boto3 credential chain
            ▼
 ┌───────────────────────────────────────────────┐
 │ AWS Credentials Source                        │
 │  A) Local user / access key / profile         │
 │  B) EC2 instance profile / IAM role           │
 └──────────┬────────────────────────────────────┘
            │
   ┌────────┴─────────┐
   ▼                  ▼
┌───────────────┐   ┌──────────────────┐
│ AWS STS       │   │ Amazon S3        │
│ Identity      │   │ Bucket Access    │
│ (Who am I?)   │   │ (What can I do?) │
└───────────────┘   └──────────────────┘
                     │
                     ├─ Test A: credentials available?
                     ├─ Test B: ListBucket works?
                     ├─ Test C: GetObject works?
                     └─ Test D: PutObject works?
```

### Scenario logic diagram

```text
No credentials found
  -> DO NOT HAVE ACCESS TO AWS / S3

Credentials found, but ListBucket denied
  -> DO NOT HAVE ACCESS TO LIST THE BUCKET

ListBucket works, but GetObject denied
  -> DO NOT HAVE READ ACCESS TO THE BUCKET OBJECTS

GetObject works, but PutObject denied
  -> DO NOT HAVE WRITE ACCESS TO THE BUCKET

ListBucket + GetObject + PutObject work
  -> FULL SUCCESS + gallery + upload works
```

### Identity source examples

- **Local laptop / workstation:**
  - AWS CLI profile
  - environment variables
  - IAM user access key
- **EC2 classroom instance:**
  - preferred approach: **instance profile / IAM role**
  - no hardcoded credentials needed in the code

## Key idea: authentication vs authorization

- **STS `GetCallerIdentity`** answers: **Who am I?**
- **S3 tests** answer: **What can I do?**

That distinction is the core teaching point of the project.

## Repository access

This repository is public.

HTTPS:

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
```

SSH:

```bash
git clone git@github.com:jodouma/ec2-iam-s3-lab.git
```

## Quick start

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open locally:

```text
http://127.0.0.1:5000
```

EC2 examples:

- `http://<ec2-public-ip>:5000`
- `http://<ec2-public-ip>` when running on port 80

## Running the app

### Development

Direct:

```bash
python3 app.py
```

Helper script:

```bash
bash scripts/run-dev.sh
```

### Classroom / public EC2 access

Helper script:

```bash
bash scripts/run-prod.sh
```

Direct:

```bash
PORT=80 HOST=0.0.0.0 python3 app.py
```

Notes:

- Port 80 may require `sudo` depending on the OS
- On EC2, open port 80 or 5000 in the Security Group
- Scripts fail cleanly if `.venv` is missing

## OS setup

### Amazon Linux 2023

```bash
sudo dnf update -y
sudo dnf install -y git python3 python3-pip curl unzip
```

Optional AWS CLI:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
```

### Ubuntu

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl unzip
```

Optional AWS CLI:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
```

### macOS

```bash
brew update
brew install git python awscli
```

macOS usually uses `zsh`, but virtualenv activation is still:

```bash
source .venv/bin/activate
```

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `AWS_REGION` | Optional AWS region override | unset |
| `S3_BUCKET_NAME` | Target bucket | `leaders-university-1337` |
| `S3_UPLOAD_PREFIX` | Upload prefix | `uploads/` |
| `FLASK_ENV` | Flask environment mode | unset |
| `HOST` | Bind address | `0.0.0.0` |
| `PORT` | Port used by the app | `5000` |

Example:

```bash
export S3_BUCKET_NAME=leaders-university-1337
export HOST=127.0.0.1
export PORT=5000
python3 app.py
```

## How credentials work

The app uses the standard boto3 / botocore credential provider chain. It can discover credentials from sources such as:

- environment variables such as `AWS_ACCESS_KEY_ID`
- local shared credentials and config profiles
- assume-role profiles
- SSO / IAM Identity Center
- container credentials
- EC2 instance metadata for an attached IAM role

The important teaching point is that **the code does not embed credentials**. On EC2, the safest and most scalable pattern is to attach an IAM role to the instance and let AWS provide temporary credentials automatically.

## AWS CLI setup and verification

The app itself uses the standard boto3 credential chain, but the AWS CLI is useful for verifying identity and testing the environment before class.

After installing AWS CLI, you can test your environment with:

```bash
aws --version
aws sts get-caller-identity
```

Examples:

- On EC2 with an attached IAM role, `aws sts get-caller-identity` should return the instance role identity
- On your laptop, it will use your configured profile or environment variables

Optional local configuration example:

```bash
aws configure
aws sts get-caller-identity
```

This is especially helpful before launching the app so you can confirm the machine has usable AWS access.

## IAM role demo flow

1. **No role attached**
   - UI: `DO NOT HAVE ACCESS TO AWS / S3`
2. **Role attached, no S3 permissions**
   - UI: `DO NOT HAVE ACCESS TO LIST THE BUCKET`
3. **Grant `s3:ListBucket` only**
   - UI: `DO NOT HAVE READ ACCESS TO THE BUCKET OBJECTS`
4. **Grant `s3:GetObject`**
   - UI: `DO NOT HAVE WRITE ACCESS TO THE BUCKET`
   - gallery loads
5. **Grant `s3:PutObject`**
   - UI: full success
   - uploads work

Policy examples for this sequence are included in `policies/`.

## Included files

- `app.py` — Flask app and AWS diagnostic logic
- `scripts/run-dev.sh` — helper script for localhost development
- `scripts/run-prod.sh` — helper script for 0.0.0.0 / port 80 classroom access
- `policies/` — IAM policy examples for the lab stages
- `docs/` — classroom support documentation
- `.env.example` — sample environment variables

## API endpoints

- `GET /` - web UI
- `GET /api/diagnostics` - returns structured diagnostics JSON
- `GET /api/images` - lists image objects when read access exists
- `GET /image/<key>` - serves image bytes through the backend
- `POST /api/upload-demo-image` - uploads a generated PNG demo image
- `POST /api/refresh` - reruns diagnostics

## Why IAM roles matter

Prefer **IAM roles** over embedded access keys:

- no hardcoded credentials in code
- temporary AWS credentials
- easier rotation and safer operations
- better EC2 security practice

## Footer signature

The UI includes a small classroom footer:

```text
Leaders University - Youssef Douma
```