import os
import csv

def get_csv_data(folder_path):
    folder_name = os.path.basename(os.path.normpath(folder_path))
    if not folder_name:
        folder_name = "images"
    csv_path = os.path.join(folder_path, f"{folder_name}.csv")
    
    if not os.path.exists(csv_path):
        return None, None, None, None
        
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        headers = next(reader, [])
        if "Filename" not in headers:
            return csv_path, headers, [], -1
            
        filename_idx = headers.index("Filename")
        rows = list(reader)
        return csv_path, headers, rows, filename_idx

def save_csv_data(csv_path, headers, rows):
    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)
        
    try:
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(csv_path), 2)
    except Exception:
        pass
