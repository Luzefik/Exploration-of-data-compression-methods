"""
testing video frames
"""
import cv2

capture = cv2.VideoCapture('./5 second rick roll.mp4')
number_frame = 0

while True:
    success, frame = capture.read()
    if success:
        cv2.imwrite(f'./res/frame_{number_frame}.jpg', frame)
    else:
        break
    number_frame += 1

capture.release()
