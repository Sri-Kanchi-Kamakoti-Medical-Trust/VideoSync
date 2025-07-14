import os
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

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

def compute_laplacian_variance_from_video(video_path, max_frames=1000):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    frame_interval = int(fps)  # Process one frame per second
    variances = []

    while cap.isOpened() and len(variances) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % frame_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()
            variances.append(variance)
            
        frame_count += 1
    
    cap.release()

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
    
def clip_video(input_path, output_path, start_time: int) -> bool:
    """Clip video from start_time to end for anonymization using moviepy"""
    try:
        cap = cv2.VideoCapture(input_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        end_time = frame_count / fps
        
        # Use moviepy to clip the video
        ffmpeg_extract_subclip(input_path, start_time, end_time, outputfile=output_path)
        print(f"Video clipped successfully from {start_time} seconds to {end_time} seconds.")

    except Exception as e:
        print(f"Error clipping video: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True
    
if __name__ == "__main__":
    video_path = "video_path"

    max_frames = 300

    # variances = compute_laplacian_variance_from_video(video_path, max_frames)
    
    # import matplotlib.pyplot as plt
    # plt.plot(variances)
    # plt.title("Laplacian Variance")
    # plt.xlabel("Frame Index")
    # plt.ylabel("Variance")
    # plt.savefig("laplacian_variance.png")
    # plt.close()

    # window_start, window_end = detect_case_sheet(variances)
    # print(f"Case sheet detected from {window_start} to {window_end} frames.")
    
    window_end = 48

    if window_end is not None:
        # Clip the video using moviepy
        output_path = "clipped.mp4"
        success = clip_video(video_path, output_path, window_end)
        if success:
            print(f"Video clipped and saved to {output_path}")