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

## How to run locally

```bash
cd /home/jo/workspace/iam-role-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open: http://127.0.0.1:5000

## Installation steps

```bash
git clone <your-repo-url> iam-role-s3-lab
cd iam-role-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional, for your own reference
python3 app.py
```

If you do not want to clone, you can also copy the project folder directly onto the machine.

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
2. Copy the project onto the instance.
3. Attach an IAM role to the instance.
4. Allow inbound access in the EC2 Security Group:
   - port `80` from your classroom/public IP range, or `0.0.0.0/0` if this is only a temporary lab
5. Install dependencies and run:

```bash
cd /home/ec2-user/iam-role-s3-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo PORT=80 /home/ec2-user/iam-role-s3-lab/.venv/bin/python3 app.py
```

Then visit:

```text
http://<ec2-public-ip>
```

Because the app listens on `0.0.0.0`, it is reachable externally when the EC2 security group and OS firewall allow the chosen port.

If you prefer not to run Python directly on port 80, you can keep the app on port 5000 and place Nginx in front of it as a reverse proxy.

## Accessing via web on a public EC2 instance

For the simple classroom path:

1. Start the app with `PORT=80`
2. Ensure the EC2 Security Group allows inbound TCP 80
3. Open the public URL in a browser:

```text
http://<ec2-public-ip>
```

The app already binds to `0.0.0.0`, so using the public EC2 IP works once networking is opened correctly.

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

## Git notes

To save the current project to the local git repository:

```bash
cd /home/jo/workspace/iam-role-s3-lab
git add .
git commit -m "Initial IAM role S3 classroom lab"
```

This project was prepared locally only and has not been pushed anywhere.

## Suggested class script summary

- Start with no role and explain the credential chain
- Add the role and show identity detection
- Add only list permission and show why bucket-level access is different from object-level access
- Add read permission and show the gallery unlock
- Add write permission and demonstrate upload success
- Close by discussing **least privilege** and why EC2 roles are safer than storing keys inside apps