import random
from ultralytics import YOLO

class ShrimpDetector:
    def __init__(self, model_path="models\YOLOshrimp.pt"):
        self.model = YOLO(model_path)

    def detect(self, frame):
        try:
            results = self.model.predict(frame, verbose=False)
            count = 0
            for r in results:
                if r.boxes:
                    count += len(r.boxes)
            return count, results
        except Exception:
            # fallback dummy data for testing
            return random.randint(5, 25), None
