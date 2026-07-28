import os
import sys
sys.path.append(r'C:\Users\david\Desktop\to organize\photoalbum_orderer')
from core.comparer import load_file_data, hamming_distance
import cv2

folder = r'C:\Users\david\Desktop\to organize\photoalbum_orderer\TEST\2026_Battesimo_Annastella_Tuzi'
data = load_file_data(folder)
data.sort(key=lambda x: x['path'])
valid_data = [d for d in data if d['hash'] is not None and d['hist'] is not None]

groups = []
hash_tol = 50 # Medio
scale = 1.0

if valid_data:
    current_group = [valid_data[0]]
    for i in range(1, len(valid_data)):
        f = valid_data[i]
        
        # Compare with the previous photo (the last one in the current group)
        prev = current_group[-1]
        
        h_dist = hamming_distance(f['hash'], prev['hash'])
        c_dist = cv2.compareHist(f['hist'], prev['hist'], cv2.HISTCMP_BHATTACHARYYA)
        
        max_hash_dist = int(35 * scale * (1 - hash_tol / 100.0))
        max_color_dist = 0.05 + 0.40 * (1 - hash_tol / 100.0)
        
        # In sequential clustering, we can be generous with color
        is_similar = False
        if c_dist <= max_color_dist:
            if c_dist < 0.20:
                is_similar = True
            elif h_dist <= max_hash_dist:
                is_similar = True
                
        if is_similar:
            current_group.append(f)
        else:
            if len(current_group) > 1:
                groups.append(current_group)
            current_group = [f]
            
    if len(current_group) > 1:
        groups.append(current_group)

print(f"Total photos: {len(valid_data)}")
print(f"Total groups formed: {len(groups)}")
for i, g in enumerate(groups):
    files = [os.path.basename(f['path']) for f in g]
    print(f"Group {i} ({len(g)} photos): {files}")
