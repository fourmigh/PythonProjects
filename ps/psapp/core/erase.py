from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


def inpaint(image: Image.Image, mask: Image.Image, radius: int = 3) -> Image.Image:
    image = image.convert("RGB")
    mask = mask.convert("L").resize(image.size)
    mask_array = np.array(mask)
    _, mask_array = cv2.threshold(mask_array, 127, 255, cv2.THRESH_BINARY)
    if int(mask_array.max()) == 0:
        return image.copy()

    rgb = np.array(image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    result = cv2.inpaint(bgr, mask_array, max(1, radius), cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
