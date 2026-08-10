import sys
import os
from pathlib import Path

# Match the production app detector behavior for trusted local model assets.
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config

CONFIGURED_MODEL_PATH = Path(config.DETECTION_MODEL_PATH)
MODEL_PATH = (
    CONFIGURED_MODEL_PATH
    if CONFIGURED_MODEL_PATH.is_absolute()
    else PROJECT_ROOT / CONFIGURED_MODEL_PATH
).resolve()

model = YOLO(str(MODEL_PATH))

print("Model loaded successfully!")
print("Model classes:")
print(model.names)
