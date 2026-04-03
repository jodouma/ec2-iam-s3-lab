# IAM Role + S3 Classroom Lab

A lightweight Flask + boto3 demo project for teaching how AWS IAM roles affect EC2 access to Amazon S3. The app is designed to make each permission stage visually obvious, so students can immediately see the difference between **no credentials**, **no list permission**, **no read permission**, **no write permission**, and **full success**.

## Project overview

This lab demonstrates five classroom scenarios against the S3 bucket `leaders-university-1337`:

1. No AWS credentials / no EC2 role
2. AWS identity exists but `ListBucket` is denied
3. Bucket listing works but object reads are denied
4. Object reads work but uploads are denied
5. All required permissions are granted

The app runs locally or on EC2. On EC2 it is intended to rely on the **instance profile / IAM role**, not hardcoded keys.

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

## How AWS credential resolution works at a high level

The app uses the standard boto3 / botocore credential provider chain. That means it can automatically discover credentials from several sources, including:

- environment variables such as `AWS_ACCESS_KEY_ID`
- local shared credentials and config profiles
- assume-role profiles
- SSO / IAM Identity Center
- container credentials
- EC2 instance metadata for an attached IAM role

The important teaching point is that **the code does not embed credentials**. On EC2, the safest and most scalable pattern is to attach an IAM role to the instance and let AWS provide temporary credentials automatically.

## Environment variables

- `AWS_REGION` - optional region override
- `S3_BUCKET_NAME` - defaults to `leaders-university-1337` and is the main place to change the target bucket dynamically
- `S3_UPLOAD_PREFIX` - defaults to `uploads/`
- `FLASK_ENV` - optional Flask environment, for example `development`
- `HOST` - bind address, defaults to `0.0.0.0`
- `PORT` - app port, defaults to `5000`; set it to `80` on EC2 if you want to access the app from the public instance IP on port 80

Example:

```bash
export S3_BUCKET_NAME=leaders-university-1337
python3 app.py
```

You can also change the active bucket live from the web UI using the **Active S3 bucket** input and **Apply Bucket** button.

## Environment Setup (Cross-Platform)

Use the section that matches your machine **before cloning the repository**. The idea is:

1. Prepare the machine
2. Install Git, Python, and AWS CLI
3. Verify the tools
4. Clone the repository
5. Create the virtual environment and run the app

### Amazon Linux 2023 (EC2)

Install the base tools first:

```bash
sudo dnf update -y
sudo dnf install -y git python3 python3-pip unzip curl
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
python3 --version
pip3 --version
git --version
aws --version
```

Optional but recommended for port 80 access in a classroom EC2 demo:

```bash
sudo setcap 'cap_net_bind_service=+ep' $(readlink -f $(which python3))
```

Or simply run the production script with `sudo`.

After setup, clone the repository:

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
```

### Ubuntu 20.04+

Install the required tools first:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
python3 --version
pip3 --version
git --version
aws --version
```

If you want the app directly on port 80, either run the production script with `sudo` or place Nginx in front of the Flask app.

After setup, clone the repository:

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
```

### macOS (Intel and Apple Silicon)

Install the required tools first. Most modern macOS systems already include Python 3, but installing current tooling with Homebrew is recommended.

```bash
brew update
brew install git python awscli
python3 --version
pip3 --version
git --version
aws --version
```

If Homebrew is not installed, see: https://brew.sh/

After setup, clone the repository:

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
```

## Repository access and clone options

This is a **public repository**:

- HTTPS works without SSH setup
- SSH requires that your public SSH key is added to your GitHub account

### Clone with HTTPS

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
```

### Clone with SSH

```bash
git clone git@github.com:jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
```

## Installation steps

After your machine is prepared and the repository is cloned:

```bash
cd ec2-iam-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional, for your own reference
python3 app.py
```

Open locally at:

```text
http://127.0.0.1:5000
```

If you do not want to clone, you can also copy the project folder directly onto the machine.

## How to run locally

```bash
cd /home/jo/workspace/iam-role-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open: http://127.0.0.1:5000

## Run scripts

Two helper scripts are included:

- `scripts/run-dev.sh` → runs the app for development on `127.0.0.1:5000`
- `scripts/run-prod.sh` → runs the app for production-style classroom demos on `0.0.0.0:80`

Examples:

```bash
cd /home/jo/workspace/iam-role-s3-lab
bash scripts/run-dev.sh
```

```bash
cd /home/jo/workspace/iam-role-s3-lab
sudo bash scripts/run-prod.sh
```

For local testing, use the standard AWS credential chain. Examples:

- export environment variables temporarily
- use `aws configure`
- use `AWS_PROFILE=your-profile python3 app.py`

Do **not** hardcode keys into the project.

## How to run on EC2

1. Launch an EC2 instance with Python 3 installed.
2. Clone the public repository onto the instance:

```bash
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
```

3. Attach an IAM role to the instance.
4. Allow inbound access in the EC2 Security Group:
   - port `80` from your classroom/public IP range, or `0.0.0.0/0` if this is only a temporary lab
5. Install dependencies and run:

```bash
cd /home/ec2-user/ec2-iam-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo PORT=80 /home/ec2-user/ec2-iam-s3-lab/.venv/bin/python3 app.py
```

Then visit:

```text
http://<ec2-public-ip>
```

Because the app listens on `0.0.0.0`, it is reachable externally when the EC2 security group and OS firewall allow the chosen port.

If you prefer not to run Python directly on port 80, you can keep the app on port 5000 and place Nginx in front of it as a reverse proxy.

## Quick start by operating system

### Amazon Linux 2023 quick start

```bash
sudo dnf update -y
sudo dnf install -y git python3 python3-pip unzip curl
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run-dev.sh
```

### Ubuntu quick start

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run-dev.sh
```

### macOS quick start

```bash
brew update
brew install git python awscli
git clone https://github.com/jodouma/ec2-iam-s3-lab.git
cd ec2-iam-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/run-dev.sh
```

## Accessing via web on a public EC2 instance

For the simple classroom path:

1. Start the app with `PORT=80`
2. Ensure the EC2 Security Group allows inbound TCP 80
3. Open the public URL in a browser:

```text
http://<ec2-public-ip>
```

The app already binds to `0.0.0.0`, so using the public EC2 IP works once networking is opened correctly.

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

## How to attach an IAM role to EC2

1. Create an IAM role for EC2.
2. Use the trust policy in `policies/ec2-trust-policy.json`.
3. Attach one of the demo S3 policies from the `policies/` folder.
4. In the EC2 console, select the instance.
5. Choose **Actions → Security → Modify IAM role**.
6. Select the role and save.
7. Refresh the app and observe the behavior change.

## Exact demo flow for class

Use the app while progressively changing the EC2 role permissions.

1. **No role attached**  
   App should show: **DO NOT HAVE ACCESS TO AWS / S3**
2. **Role attached, no S3 permissions**  
   App should show: **DO NOT HAVE ACCESS TO LIST THE BUCKET**
3. **Grant `s3:ListBucket` only**  
   App should show: **DO NOT HAVE READ ACCESS TO THE BUCKET OBJECTS**
4. **Grant `s3:GetObject` in addition**  
   App should show: **DO NOT HAVE WRITE ACCESS TO THE BUCKET** and gallery should load
5. **Grant `s3:PutObject`**  
   App should show full success and demo uploads should work

## Sequence of permission changes to demonstrate each failure mode

Recommended progression:

1. No IAM role attached to the EC2 instance
2. Attach EC2 role with no S3 policy
3. Attach `02-listbucket-policy.json`
4. Replace with or add `03-getobject-policy.json`
5. Replace with or add `04-putobject-policy.json`
6. Optionally use `05-full-access-policy.json` as the final role policy set

## API endpoints

- `GET /` - web UI
- `GET /api/diagnostics` - returns structured diagnostics JSON
- `GET /api/images` - lists image objects when read access exists
- `GET /image/<key>` - serves image bytes through the backend
- `POST /api/upload-demo-image` - uploads a generated PNG demo image
- `POST /api/refresh` - reruns diagnostics

## Security note

Prefer **IAM roles** over embedded access keys. Roles provide temporary credentials, reduce secret sprawl, simplify rotation, and are the recommended AWS approach for EC2 workloads.

## Suggested class script summary

- Start with no role and explain the credential chain
- Add the role and show identity detection
- Add only list permission and show why bucket-level access is different from object-level access
- Add read permission and show the gallery unlock
- Add write permission and demonstrate upload success
- Close by discussing **least privilege** and why EC2 roles are safer than storing keys inside apps