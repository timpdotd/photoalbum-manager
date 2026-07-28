import os
import base64
import numpy as np
from PIL import Image
import imagehash
import cv2
from core.csv_manager import get_csv_data, save_csv_data
from core.scanner import is_video_file
from core.logger import get_logger

def process_perceptual_hash(folder_path, force=False):
    csv_path, headers, rows, filename_idx = get_csv_data(folder_path)
    if csv_path is None or filename_idx == -1: return 0
    
    if "PerceptualHash" not in headers:
        headers.append("PerceptualHash")
    if "ColorHist" not in headers:
        headers.append("ColorHist")
    if "AI_Feat" not in headers:
        headers.append("AI_Feat")
    if "HOG_Feat" not in headers:
        headers.append("HOG_Feat")
        
    hash_idx = headers.index("PerceptualHash")
    hist_idx = headers.index("ColorHist")
    ai_idx = headers.index("AI_Feat")
    hog_idx = headers.index("HOG_Feat")
    
    processed = 0
    for row in rows:
        while len(row) <= max(hash_idx, hist_idx, ai_idx, hog_idx):
            row.append("")
            
        if not row[hash_idx] or not row[hist_idx] or not row[ai_idx] or not row[hog_idx] or force:
            img_filename = row[filename_idx]
            img_path = os.path.join(folder_path, img_filename)
            if os.path.exists(img_path):
                try:
                    img_cv = None
                    img_pil = None
                    
                    if is_video_file(img_filename):
                        cap = cv2.VideoCapture(img_path)
                        ret, frame = cap.read()
                        if ret:
                            img_cv = frame # Mantiene BGR per cv2
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            img_pil = Image.fromarray(frame_rgb)
                        cap.release()
                    else:
                        img_cv = cv2.imread(img_path)
                        if img_cv is not None:
                            img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
                        
                    if img_pil is not None and img_cv is not None:
                        # 1. pHash (struttura) a 64 bit classici
                        phash = str(imagehash.phash(img_pil))
                        row[hash_idx] = phash
                        
                        # 2. Color Histogram (HSV)
                        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
                        # Istogramma 2D su Tinta (Hue) e Saturazione (16 bins per asse = 256 valori totali)
                        hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
                        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
                        
                        # Serializzazione in Base64 (veloce e sicuro per CSV)
                        hist_b64 = base64.b64encode(hist.astype(np.float32).tobytes()).decode('utf-8')
                        row[hist_idx] = hist_b64
                        
                        # 3. AI Semantic Features
                        from core.ai_processor import get_ai_processor
                        ai_feat = get_ai_processor().extract_features(img_pil)
                        ai_b64 = get_ai_processor().serialize_features(ai_feat)
                        
                        if "AI_Feat" not in headers:
                            headers.append("AI_Feat")
                        
                        ai_idx = headers.index("AI_Feat")
                        while len(row) <= ai_idx:
                            row.append("")
                        row[ai_idx] = ai_b64
                        
                        # 4. HOG Features
                        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                        img_gray_resized = cv2.resize(img_gray, (64, 64))
                        hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)
                        hog_feat = hog.compute(img_gray_resized).flatten().astype(np.float32)
                        hog_b64 = base64.b64encode(hog_feat.tobytes()).decode('utf-8')
                        
                        if "HOG_Feat" not in headers:
                            headers.append("HOG_Feat")
                            
                        hog_idx = headers.index("HOG_Feat")
                        while len(row) <= hog_idx:
                            row.append("")
                        row[hog_idx] = hog_b64
                        
                        processed += 1
                except Exception as e:
                    get_logger().error(f"Errore calcolo hash ibrido per {img_path}: {e}")
                    
    if processed > 0:
        save_csv_data(csv_path, headers, rows)
    return processed
