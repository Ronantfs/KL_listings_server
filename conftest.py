import sys
from unittest.mock import MagicMock

# Mock external/side-effectful modules before any test imports lambda_function
# or shared.config, to prevent module-level S3 client initialisation.
sys.modules.setdefault("shared.aws", MagicMock())
sys.modules.setdefault("dotenv", MagicMock())
