# Teacher Guide

## 10-15 minute classroom walkthrough

This lab works best as a live demonstration where the teacher changes one permission at a time and asks students to predict the next result before refreshing the page.

### Minute 1-2: Introduce the problem

What to say:

- “Applications on EC2 often need AWS access.”
- “We do not want to store access keys in code or on disk if we can avoid it.”
- “Today we will let AWS provide temporary credentials through an EC2 IAM role.”

Expected app output:

- If no credentials are available, the app shows **DO NOT HAVE ACCESS TO AWS / S3**.

### Minute 3-4: Show no role attached

What to say:

- “Right now the server has no usable AWS credentials.”
- “Without credentials, even identifying who we are is impossible.”

Expected output:

- Big red banner: **DO NOT HAVE ACCESS TO AWS / S3**
- Diagnostics should show credential lookup failure.

### Minute 5-6: Attach the role, but no S3 permissions

What to say:

- “Now the app has an identity.”
- “But identity alone is not permission.”

Expected output:

- Banner: **DO NOT HAVE ACCESS TO LIST THE BUCKET**
- Identity card should show account and ARN
- Diagnostics should show STS working and S3 listing failing.

### Minute 7-8: Add `s3:ListBucket`

What to say:

- “Bucket-level and object-level permissions are different.”
- “Listing the bucket does not automatically allow reading files.”

Expected output:

- Banner: **DO NOT HAVE READ ACCESS TO THE BUCKET OBJECTS**
- Diagnostics should show listing success and read failure.

### Minute 9-10: Add `s3:GetObject`

What to say:

- “Now the app can enumerate keys and read image data.”
- “Notice that upload is still blocked.”

Expected output:

- Banner: **DO NOT HAVE WRITE ACCESS TO THE BUCKET**
- Animated gallery appears
- Upload test fails.

### Minute 11-12: Add `s3:PutObject`

What to say:

- “Now the app has exactly the operations it needs.”
- “This is a least-privilege policy set for our lab behavior.”

Expected output:

- Green success banner
- Gallery visible
- Upload button succeeds and the new image appears after refresh.

### Minute 13-15: Wrap-up discussion

What to say:

- “Least privilege means granting only the actions the app truly needs.”
- “Roles are safer because the app receives temporary credentials automatically.”
- “If we embedded keys in code, we would create rotation, storage, and leakage risks.”

## How to explain least privilege

Use this progression:

1. The app starts with no access.
2. Add only the minimum next permission.
3. Show exactly what new capability appears.
4. Stop once the app can do its job.

That makes least privilege concrete rather than abstract.

## How to explain why EC2 roles are safer than app credentials

- No long-lived secret needs to be committed or copied into the app
- Temporary credentials are issued automatically by AWS
- Rotation is handled by AWS
- Centralized policy management is easier to audit
- Reusing the app on many instances is safer because the identity belongs to the infrastructure role, not an embedded key