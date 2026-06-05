from paddleocr import PaddleOCR
import numpy as np
import cv2


class OCRService:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang="en")

    async def extract_text(self, image_bytes: bytes) -> str:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        result = self.ocr.ocr(img, cls=True)

        text = []
        for line in result[0]:
            text.append(line[1][0])

        return "\n".join(text)