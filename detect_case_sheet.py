import os
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

def extract_frames(video_path, output_dir, max_frames=1000):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    saved_frames = 0
    frame_interval = int(fps)  # Save one frame per second

    while cap.isOpened() and saved_frames < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            # print(f"Extracting frame {saved_frames + 1} at {frame_count / fps:.2f} seconds")
            out_path = os.path.join(output_dir, f"frame_{saved_frames:04d}.jpg")
            cv2.imwrite(out_path, frame)
            saved_frames += 1
        frame_count += 1
    cap.release()
    return fps, saved_frames

def compute_laplacian_variance(frame_dir):
    variances = []
    frame_paths = sorted([os.path.join(frame_dir, f) for f in os.listdir(frame_dir) if f.endswith('.jpg')])
    for path in frame_paths:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        laplacian = cv2.Laplacian(img, cv2.CV_64F)
        variance = laplacian.var()
        variances.append(variance)

    return np.array(variances)

def detect_case_sheet(variances):
    variances = gaussian_filter1d(variances, sigma=2)

    threshold = 12
    window_size = 15
    window_st = None
    # check the last window where avg < threshold
    for i in range(0, len(variances) - window_size):
        if np.mean(variances[i:i + window_size]) < threshold:
            window_st = i

    if window_st is not None:
        print(f"Time: {window_st+window_size} seconds")

        return window_st, window_st + window_size
    else:
        print("No window found with average variance below threshold.")
        return None, None