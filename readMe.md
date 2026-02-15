python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m pip list

#for lambda build:
# 2️⃣ Activate the virtual environment
venv\Scripts\Activate.ps1

# 3️⃣ Install required packages into the venv
pip install -r requirements.txt

# 4️⃣ Create a build directory
New-Item -ItemType Directory -Force -Path build | Out-Null

# 5️⃣ Install dependencies into the build folder (for Lambda package)
pip install -r requirements.txt -t build/

# 6️⃣ Copy your Lambda code into the build folder
Copy-Item lambda_function.py build/
Copy-Item modules build/

# 7️⃣ Zip everything inside the build folder
Compress-Archive -Path build\* -DestinationPath lambda_package.zip -Force


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
