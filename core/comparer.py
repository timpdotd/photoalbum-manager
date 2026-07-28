import os
import csv
import base64
import numpy as np
import cv2
from core.scanner import find_image_folders, is_video_file

class UnionFind:
    def __init__(self):
        self.parent = {}
    
    def find(self, i):
        if self.parent.setdefault(i, i) == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]
    
    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j

def hex_to_hash(hexstr):
    try:
        return int(hexstr, 16)
    except:
        return None

def hamming_distance(h1, h2):
    x = h1 ^ h2
    return bin(x).count('1')

def cosine_similarity(v1, v2):
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot / (norm1 * norm2)

def load_file_data(folder_path):
    """Carica i dati di hash dal CSV per la cartella specificata."""
    folder_name = os.path.basename(os.path.normpath(folder_path))
    if not folder_name:
        folder_name = "images"
    csv_path = os.path.join(folder_path, f"{folder_name}.csv")
    
    data = []
    if not os.path.exists(csv_path):
        return data
        
    with open(csv_path, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        
        if "Filename" not in headers: return data
        filename_idx = headers.index("Filename")
        
        hash_idx = headers.index("PerceptualHash") if "PerceptualHash" in headers else -1
        hist_idx = headers.index("ColorHist") if "ColorHist" in headers else -1
        
        for row in reader:
            if not row: continue
            fname = row[filename_idx]
            file_path = os.path.join(folder_path, fname)
            
            # Salta i file fantasma (es. eliminati manualmente dall'utente)
            if not os.path.exists(file_path):
                continue
            
            phash = None
            hash_len = 0
            if hash_idx != -1 and len(row) > hash_idx and row[hash_idx]:
                hash_len = len(row[hash_idx])
                phash = hex_to_hash(row[hash_idx])
                
            hist = None
            if hist_idx != -1 and len(row) > hist_idx and row[hist_idx]:
                try:
                    hist_bytes = base64.b64decode(row[hist_idx])
                    hist = np.frombuffer(hist_bytes, dtype=np.float32).reshape(16, 16)
                except Exception:
                    pass
                    
            ai_feat = None
            ai_idx = headers.index("AI_Feat") if "AI_Feat" in headers else -1
            if ai_idx != -1 and len(row) > ai_idx and row[ai_idx]:
                try:
                    ai_bytes = base64.b64decode(row[ai_idx])
                    ai_feat = np.frombuffer(ai_bytes, dtype=np.float16).astype(np.float32)
                except Exception:
                    pass
                    
            hog_feat = None
            hog_idx = headers.index("HOG_Feat") if "HOG_Feat" in headers else -1
            if hog_idx != -1 and len(row) > hog_idx and row[hog_idx]:
                try:
                    hog_bytes = base64.b64decode(row[hog_idx])
                    hog_feat = np.frombuffer(hog_bytes, dtype=np.float32)
                except Exception:
                    pass
                    
            data.append({
                'path': file_path,
                'hash': phash,
                'hash_len': hash_len,
                'hist': hist,
                'ai_feat': ai_feat,
                'hog_feat': hog_feat
            })
    return data

class Comparer:
    def __init__(self, target_folder, root_path, hash_tol):
        self.target_folder = target_folder
        self.root_path = root_path
        self.hash_tol = hash_tol # 0-100
        
        # Mapping tolleranza Hash (100% = 0 distanza, 0% = 25 distanza)
        self.max_hash_dist = int(25 * (1 - self.hash_tol / 100.0))
        
    def _get_groups_for_method(self, files, method):
        groups = []
        current_group = []
        
        for f in files:
            if f['hash'] is None or f['hist'] is None:
                continue
                
            if not current_group:
                current_group.append(f)
                continue
                
            # Sequential Clustering: confrontiamo solo con il leader della raffica corrente
            leader = current_group[0]
            
            # NON mischiare foto e video nello stesso gruppo
            if f['is_video'] != leader['is_video'] or f['hash_len'] != leader['hash_len']:
                groups.append(current_group)
                current_group = [f]
                continue
                
            is_similar = False
            
            if method == "ai" and f.get('ai_feat') is not None and leader.get('ai_feat') is not None:
                # Distanza del Coseno per AI
                min_cos = 0.65 + 0.30 * (self.hash_tol / 100.0)
                sim = cosine_similarity(f['ai_feat'], leader['ai_feat'])
                if sim >= min_cos:
                    is_similar = True
            elif method == "hog" and f.get('hog_feat') is not None and leader.get('hog_feat') is not None:
                # Distanza Euclidea per HOG
                dist = np.linalg.norm(f['hog_feat'] - leader['hog_feat'])
                max_dist = 0.8 - 0.65 * (self.hash_tol / 100.0)
                if dist <= max_dist:
                    is_similar = True
            elif method == "ibrido":
                # Logica Ibrida
                dist_hash = hamming_distance(f['hash'], leader['hash'])
                scale = f['hash_len'] / 16.0
                dist_color = cv2.compareHist(f['hist'], leader['hist'], cv2.HISTCMP_BHATTACHARYYA)
                max_hash_dist = int(45 * scale * (1 - self.hash_tol / 100.0))
                max_color_dist = 0.05 + 0.45 * (1 - self.hash_tol / 100.0)
                bypass_color_dist = 0.02 + 0.23 * (1 - self.hash_tol / 100.0)
                
                if dist_color <= max_color_dist:
                    if dist_color <= bypass_color_dist:
                        is_similar = True
                    elif dist_hash <= max_hash_dist:
                        is_similar = True
                        
            if is_similar:
                current_group.append(f)
            else:
                groups.append(current_group)
                current_group = [f]
                
        if current_group:
            groups.append(current_group)
            
        return groups
        
    def run(self, progress_callback):
        # Cerca duplicati a partire dalla cartella selezionata dall'utente
        folders = find_image_folders(self.target_folder)
        if not folders:
            return {}
            
        final_results = {}
        
        # Confronto isolato per singola sottocartella
        total_folders = len(folders)
        for idx, folder in enumerate(folders):
            files = load_file_data(folder)
            if len(files) < 2: 
                prog = int(((idx + 1) / total_folders) * 100)
                progress_callback(prog)
                continue
            
            # Ordina i file per percorso/nome per garantire che le raffiche siano raggruppate cronologicamente
            files.sort(key=lambda x: x['path'])
            
            # Pre-calcola se è video o foto per ottimizzare il ciclo interno
            for f in files:
                f['is_video'] = is_video_file(f['path'])
                
            # Inizializza l'Union-Find
            uf = UnionFind()
            file_to_idx = {f['path']: i for i, f in enumerate(files)}
            for i in range(len(files)):
                uf.find(i) # initialize roots
                
            # Esegue il clustering per tutti e 3 i metodi e unisce i risultati
            for method in ["ai", "hog", "ibrido"]:
                method_groups = self._get_groups_for_method(files, method)
                for g in method_groups:
                    if len(g) > 1:
                        root_idx = file_to_idx[g[0]['path']]
                        for i in range(1, len(g)):
                            uf.union(root_idx, file_to_idx[g[i]['path']])
                            
            # Raggruppa i file finali basandosi sui componenti connessi dell'Union-Find
            component_to_files = {}
            for f in files:
                if f['hash'] is None or f['hist'] is None:
                    continue
                idx = file_to_idx[f['path']]
                root = uf.find(idx)
                if root not in component_to_files:
                    component_to_files[root] = []
                component_to_files[root].append(f)
            
            folder_groups = []
            for comp_files in component_to_files.values():
                if len(comp_files) > 1:
                    # Garantiamo che all'interno del gruppo finale l'ordine sia mantenuto
                    comp_files.sort(key=lambda x: x['path'])
                    folder_groups.append([f['path'] for f in comp_files])
                    
            if folder_groups:
                final_results[folder] = folder_groups
                
            prog = int(((idx + 1) / total_folders) * 100)
            progress_callback(prog)
            
        progress_callback(100)
        return final_results
