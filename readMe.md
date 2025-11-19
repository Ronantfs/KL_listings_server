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
