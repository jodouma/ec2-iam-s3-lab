# Demo Scenarios

## Scenario 1: no role attached

- No EC2 instance role or no usable local credentials
- The app should fail at the credential stage

### UI should show

- Banner: **DO NOT HAVE ACCESS TO AWS / S3**
- Diagnostics: credentials fail, list/read/write all unavailable
- Identity card: no caller identity or failed STS lookup

## Scenario 2: role attached but no S3 permissions

- EC2 role exists and STS identity works
- No S3 policy is attached

### UI should show

- Banner: **DO NOT HAVE ACCESS TO LIST THE BUCKET**
- Diagnostics: credentials yes, list no, read no, write no
- Identity card: account + ARN visible

## Scenario 3: role has ListBucket only

- Policy includes only `s3:ListBucket`

### UI should show

- Banner: **DO NOT HAVE READ ACCESS TO THE BUCKET OBJECTS**
- Diagnostics: credentials yes, list yes, read no, write no
- Gallery: hidden because object reads fail

## Scenario 4: role has ListBucket + GetObject only

- Policy includes `s3:ListBucket` and `s3:GetObject`

### UI should show

- Banner: **DO NOT HAVE WRITE ACCESS TO THE BUCKET**
- Diagnostics: credentials yes, list yes, read yes, write no
- Gallery: visible and populated with bucket images
- Upload button: fails cleanly with technical details available

## Scenario 5: role has ListBucket + GetObject + PutObject

- Policy includes `s3:ListBucket`, `s3:GetObject`, and `s3:PutObject`

### UI should show

- Banner: full success state
- Diagnostics: credentials yes, list yes, read yes, write yes
- Gallery: visible
- Upload button: succeeds and newly uploaded image appears after refresh