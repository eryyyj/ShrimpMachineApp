import os
import sys
import time
import cv2
import numpy as np

# ---- Ensure ONNXRuntime DLLs load properly (Windows safety) ----
onnx_dll_path = os.path.join(sys.prefix, "Lib", "site-packages", "onnxruntime", "capi")
if os.path.exists(onnx_dll_path):
    try:
        os.add_dll_directory(onnx_dll_path)
    except Exception:
        pass

import onnxruntime as ort


class ShrimpDetector:
    def __init__(self, model_path="models/YOLOshrimp.onnx", conf_thresh=0.25, imgsz=416):
        """Initialize ONNX model session."""
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.imgsz = imgsz

        try:
            self.session = ort.InferenceSession(
                model_path, providers=["CPUExecutionProvider"]
            )
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [o.name for o in self.session.get_outputs()]
            print(f" Loaded ONNX model: {model_path}")
        except Exception as e:
            print(" Failed to load ONNX model:", e)
            self.session = None

    # ---------------------------------------------------------------
    # Preprocess: resize + letterbox (maintain aspect ratio)
    # ---------------------------------------------------------------
    def preprocess(self, frame):
        h, w = frame.shape[:2]
        scale = min(self.imgsz / w, self.imgsz / h)
        nw, nh = int(w * scale), int(h * scale)

        resized = cv2.resize(frame, (nw, nh))
        top = (self.imgsz - nh) // 2
        bottom = self.imgsz - nh - top
        left = (self.imgsz - nw) // 2
        right = self.imgsz - nw - left

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right,
            cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )

        img = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        img = img.transpose(2, 0, 1) / 255.0
        img = np.expand_dims(img, axis=0).astype(np.float32)
        return img, scale, left, top

    # ---------------------------------------------------------------
    # Detect and visualize
    # ---------------------------------------------------------------
    def detect(self, frame, draw=True):
        if self.session is None:
            return 0, frame

        h, w = frame.shape[:2]
        input_tensor, scale, pad_x, pad_y = self.preprocess(frame)

        # ---- Run inference ----
        start = time.time()
        outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
        inference_time = (time.time() - start) * 1000

        detections = []
        out = outputs[0]

        # Case 1: model already includes NMS
        if len(out.shape) == 3 and out.shape[-1] in [6, 7]:
            for det in out[0]:
                if det is None or len(det) < 6:
                    continue
                x1, y1, x2, y2, conf, cls = det[:6]
                if conf < self.conf_thresh:
                    continue

                # Reverse letterbox to map boxes back to original frame
                x1 = max((x1 - pad_x) / scale, 0)
                y1 = max((y1 - pad_y) / scale, 0)
                x2 = min((x2 - pad_x) / scale, w)
                y2 = min((y2 - pad_y) / scale, h)
                detections.append((x1, y1, x2, y2))

        # Case 2: raw output (no NMS)
        elif len(out.shape) == 3 and out.shape[-1] > 7:
            preds = out[0]
            for det in preds:
                obj_conf = det[4]
                cls_conf = det[5:].max()
                conf = obj_conf * cls_conf
                if conf < self.conf_thresh:
                    continue

                x, y, bw, bh = det[:4]

                # Reverse letterbox mapping
                x1 = (x - bw / 2 - pad_x) / scale
                y1 = (y - bh / 2 - pad_y) / scale
                x2 = (x + bw / 2 - pad_x) / scale
                y2 = (y + bh / 2 - pad_y) / scale

                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                detections.append((x1, y1, x2, y2))

        count = len(detections)

        # ---- Draw bounding boxes ----
        if draw:
            overlay = frame.copy()
            for (x1, y1, x2, y2) in detections:
                cv2.rectangle(
                    overlay,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 0),
                    1
                )

            # Semi-transparent overlay
            frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)

            fps = int(1000 / inference_time) if inference_time > 0 else 0
            cv2.putText(
                frame,
                f"{fps} FPS | Count: {count}",
                (15, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        # Return frame as RGB for PyQt display
        return count, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


# ---------------------------------------------------------------
# Stand-alone camera test (optional)
# ---------------------------------------------------------------
if __name__ == "__main__":
    detector = ShrimpDetector("models/YOLOshrimp.onnx", conf_thresh=0.25, imgsz=416)
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        count, vis = detector.detect(frame, draw=True)
        cv2.imshow("Shrimp Detector", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
