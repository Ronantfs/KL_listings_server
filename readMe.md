# Service sumamry: 
The server for the data that drives the front end of KL: 

Two "routes" (driven by query param): 
- **listings**: 
    - Desc: Raw cinema listings (film titles, showtimes, etc.) for the requested cinemas and dates, with internal fields redacted
    - Drives: Cinema Listings Index
    - Type of return (pre HTTP) #TODO
- **visual_listings** —
    - Desc:  Cinema listings filtered to only films that have a matching "good" image in S3, with a presigned image URL attached to each listing (also date-filtered and redacted)internal fields redacted
    - Drives: VPE in front end
    - Type of return (pre HTTP) #TODO


## Examples: 

### Listings: 

Invoke payload: 
``` json
{
    "httpMethod": "GET",
    "queryStringParameters": {
        "route_type": "listings",
        "cinemas": "bfi_southbank,prince_charles",
        "dates": "2026-02-19,2026-02-20"
    }
}
```

### Visual : 
Invoke payload: 
``` json
{
    "httpMethod": "GET",
    "queryStringParameters": {
        "route_type": "listings",
        "cinemas": "bfi_southbank,prince_charles",
        "dates": "2026-02-19,2026-02-20"
    }
}
```










---

# INSTAL 

MAC:
--- local dev setup:
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip list

--- Build & Deploy (recommended) ---

Uses the buildDeploy/ folder with boto3 to build the zip and deploy to AWS Lambda.

Prerequisites:
- uv installed (brew install uv)
- AWS SSO profile "ronantfs" configured (aws configure sso)
- Login to SSO before deploying: aws sso login --profile ronantfs

Build only (creates lambda_package.zip):
./buildDeploy/build_lambda.sh

Deploy only (zip must already exist):
./buildDeploy/deploy.sh --skip-build

Build + Deploy in one step:
./buildDeploy/deploy.sh

Target: arn:aws:lambda:eu-north-1:977099012524:function:kl_listings_server

VS Code: use the Run & Debug panel (Cmd+Shift+D) and select:
- "Build Lambda" - build only
- "Deploy Lambda (skip build)" - deploy existing zip
- "Build + Deploy Lambda" - full build and deploy

Or use Tasks (Cmd+Shift+P > "Tasks: Run Task") for the same options.

--- legacy lambda build:

run this once:
chmod +x build_lambda_mac.sh

then build with this:
./build_lambda_mac.sh

---
