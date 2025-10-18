import cv2

class Camera:
    def __init__(self, index=3):
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def get_frame(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self):
        self.cap.release()
