import os
import sys
sys.path.append(r'C:\Users\david\Desktop\to organize\photoalbum_orderer')
from core.comparer import load_file_data, hamming_distance
import cv2

folder = r'C:\Users\david\Desktop\to organize\photoalbum_orderer\TEST\2026_Battesimo_Annastella_Tuzi'
data = load_file_data(folder)

if not data:
    print("CSV data empty or missing.")
    sys.exit(0)

data.sort(key=lambda x: x['path'])
valid_data = [d for d in data if d['hash'] is not None and d['hist'] is not None]

print(f"Loaded {len(valid_data)} valid rows.")

if not valid_data:
    print("No valid hashes/histograms. Did you force reprocess?")
    sys.exit(0)

for i in range(len(valid_data)-1):
    d1 = valid_data[i]
    d2 = valid_data[i+1]
    
    h_dist = hamming_distance(d1['hash'], d2['hash'])
    c_dist = cv2.compareHist(d1['hist'], d2['hist'], cv2.HISTCMP_BHATTACHARYYA)
    
    f1 = os.path.basename(d1['path'])
    f2 = os.path.basename(d2['path'])
    
    if c_dist < 0.2:
        print(f'{f1} vs {f2} -> HashDist: {h_dist:2d}, ColorDist: {c_dist:.3f}')
