import os
import glob
from datetime import datetime
from PIL import Image

TEMP_DIR = ".temp"


def clear_temp():
    if os.path.isdir(TEMP_DIR):
        for f in glob.glob(os.path.join(TEMP_DIR, "*")):
            try:
                os.remove(f)
            except OSError:
                pass


def save_debug_image(image: Image.Image, label: str) -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%H%M%S_%f")
    filename = f"{timestamp}_{label}.png"
    path = os.path.join(TEMP_DIR, filename)
    image.save(path)
    return path
