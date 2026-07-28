import os
import uuid
import csv
from core.scanner import is_supported_media, is_video_file
from core.csv_manager import get_csv_data, save_csv_data

def get_file_timestamps(filepath):
    import os
    try:
        stat = os.stat(filepath)
        return stat.st_ctime, stat.st_atime, stat.st_mtime
    except:
        return None

def restore_file_timestamps(filepath, timestamps):
    if not timestamps:
        return
    c_time, a_time, m_time = timestamps
    import os
    if os.name != 'nt':
        try:
            os.utime(filepath, (a_time, m_time))
        except:
            pass
        return
        
    import ctypes
    from ctypes import wintypes
    
    def to_filetime(t):
        wtime = int((t + 11644473600) * 10000000)
        return wintypes.FILETIME(wtime & 0xFFFFFFFF, wtime >> 32)
        
    ft_creation = to_filetime(c_time)
    ft_access = to_filetime(a_time)
    ft_modification = to_filetime(m_time)
    
    CreateFileW = ctypes.windll.kernel32.CreateFileW
    SetFileTime = ctypes.windll.kernel32.SetFileTime
    CloseHandle = ctypes.windll.kernel32.CloseHandle
    
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    
    handle = CreateFileW(
        filepath,
        GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS,
        None
    )
    
    if handle != -1: # INVALID_HANDLE_VALUE
        SetFileTime(
            handle,
            ctypes.byref(ft_creation),
            ctypes.byref(ft_access),
            ctypes.byref(ft_modification)
        )
        CloseHandle(handle)

def get_sort_key(filepath):
    filename = os.path.basename(filepath)
    name, _ = os.path.splitext(filename)
    parts = name.split('_')
    if len(parts) == 2 and parts[0] in ('photo', 'video'):
        try:
            return (0, int(parts[1]), filepath)
        except ValueError:
            pass
    try:
        return (1, os.path.getmtime(filepath), filepath)
    except:
        return (2, filename, filepath)

def rename_files_chronologically(folder_path):
    # 1. Carica i dati del CSV esistente per preservare i metadati
    csv_path, headers, rows, filename_idx = get_csv_data(folder_path)
    
    # Se il CSV non esiste, creiamo intestazioni di default
    if csv_path is None:
        folder_name = os.path.basename(os.path.normpath(folder_path))
        if not folder_name:
            folder_name = "images"
        csv_path = os.path.join(folder_path, f"{folder_name}.csv")
        headers = ["Filename", "Printed", "PerceptualHash", "ColorHist", "AI_Feat"]
        rows = []
        filename_idx = 0
        
    # Crea un dizionario delle righe esistenti basato sul nome file
    existing_metadata = {}
    for row in rows:
        if row and filename_idx < len(row):
            fname = row[filename_idx]
            existing_metadata[fname] = row

    # 2. Ottieni tutti i file multimediali fisici presenti nella cartella
    physical_files = [f for f in os.listdir(folder_path) 
                      if os.path.isfile(os.path.join(folder_path, f)) and is_supported_media(f)]
                      
    photos = []
    videos = []
    
    for f in physical_files:
        path = os.path.join(folder_path, f)
        if is_video_file(f):
            videos.append(path)
        else:
            photos.append(path)
            
    # Ordina le foto e i video
    photos.sort(key=get_sort_key)
    videos.sort(key=get_sort_key)
    
    # Prepara le operazioni di rinomina
    rename_ops = [] # list of dicts: {"src": ..., "temp": ..., "dest": ..., "old_name": ..., "new_name": ...}
    
    # Genera i nomi per le foto
    for idx, src_path in enumerate(photos):
        ext = os.path.splitext(src_path)[1].lower()
        old_name = os.path.basename(src_path)
        new_name = f"photo_{idx + 1:04d}{ext}"
        
        temp_name = f"_temp_rename_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(folder_path, temp_name)
        dest_path = os.path.join(folder_path, new_name)
        
        rename_ops.append({
            "src": src_path,
            "temp": temp_path,
            "dest": dest_path,
            "old_name": old_name,
            "new_name": new_name
        })
        
    # Genera i nomi per i video
    for idx, src_path in enumerate(videos):
        ext = os.path.splitext(src_path)[1].lower()
        old_name = os.path.basename(src_path)
        new_name = f"video_{idx + 1:04d}{ext}"
        
        temp_name = f"_temp_rename_{uuid.uuid4().hex}{ext}"
        temp_path = os.path.join(folder_path, temp_name)
        dest_path = os.path.join(folder_path, new_name)
        
        rename_ops.append({
            "src": src_path,
            "temp": temp_path,
            "dest": dest_path,
            "old_name": old_name,
            "new_name": new_name
        })

    # Fase 1: Rinomina fisica a nomi temporanei (previene collisioni)
    printed_folder = os.path.join(folder_path, "Printed")
    os.makedirs(printed_folder, exist_ok=True)
    
    # Salva i timestamp originali (inclusa la data di creazione) per preservare i metadati del filesystem
    original_timestamps = {}
    printed_timestamps = {}
    for op in rename_ops:
        original_timestamps[op["src"]] = get_file_timestamps(op["src"])
        src_printed = os.path.join(printed_folder, op["old_name"])
        if os.path.exists(src_printed):
            printed_timestamps[src_printed] = get_file_timestamps(src_printed)
    
    for op in rename_ops:
        try:
            # Rinomina file principale
            os.rename(op["src"], op["temp"])
            # Rinomina file in Printed se esiste
            src_printed = os.path.join(printed_folder, op["old_name"])
            if os.path.exists(src_printed):
                temp_printed = os.path.join(printed_folder, os.path.basename(op["temp"]))
                os.rename(src_printed, temp_printed)
        except Exception as e:
            print(f"Errore rinomina temporanea per {op['old_name']}: {e}")
            
    # Fase 2: Rinomina da nomi temporanei a definitivi
    new_rows = []
    for op in rename_ops:
        try:
            # Rinomina file principale
            os.rename(op["temp"], op["dest"])
            # Ripristina la data di creazione, modifica e accesso originale del file principale
            restore_file_timestamps(op["dest"], original_timestamps.get(op["src"]))
            
            # Rinomina file in Printed se esiste
            temp_printed = os.path.join(printed_folder, os.path.basename(op["temp"]))
            if os.path.exists(temp_printed):
                dest_printed = os.path.join(printed_folder, op["new_name"])
                os.rename(temp_printed, dest_printed)
                # Ripristina la data di creazione, modifica e accesso originale del file stampato
                src_printed = os.path.join(printed_folder, op["old_name"])
                restore_file_timestamps(dest_printed, printed_timestamps.get(src_printed))
                
            # Costruisci la riga del CSV aggiornata
            old_row = existing_metadata.get(op["old_name"])
            if old_row:
                # Modifica il nome del file
                row_copy = list(old_row)
                while len(row_copy) <= filename_idx:
                    row_copy.append("")
                row_copy[filename_idx] = op["new_name"]
                new_rows.append(row_copy)
            else:
                # Crea nuova riga
                row_data = [""] * len(headers)
                row_data[filename_idx] = op["new_name"]
                # Inizializza Printed
                if "Printed" in headers:
                    printed_idx = headers.index("Printed")
                    # Controlla se il file esiste fisicamente nella cartella Printed
                    dest_printed = os.path.join(printed_folder, op["new_name"])
                    row_data[printed_idx] = "True" if os.path.exists(dest_printed) else "False"
                new_rows.append(row_data)
        except Exception as e:
            print(f"Errore rinomina definitiva da {op['temp']} a {op['new_name']}: {e}")

    # Salva il nuovo CSV
    save_csv_data(csv_path, headers, new_rows)
    
    # 3. Pulisci la cartella Printed da file fantasma che non esistono più
    active_new_names = {op["new_name"] for op in rename_ops}
    for f in os.listdir(printed_folder):
        if f not in active_new_names:
            try:
                os.remove(os.path.join(printed_folder, f))
            except:
                pass

def process_folder(folder_path):
    """
    Rinomina sequenzialmente le immagini e i video in ordine cronologico,
    preserva la cartella Printed, e aggiorna il CSV di cache.
    """
    # 1. Crea la cartella Printed se non esiste
    printed_folder = os.path.join(folder_path, "Printed")
    os.makedirs(printed_folder, exist_ok=True)
    
    # 2. Esegui la rinomina e l'aggiornamento CSV
    rename_files_chronologically(folder_path)
    
    # 3. Conta gli elementi per restituire il risultato
    images = [f for f in os.listdir(folder_path) 
              if os.path.isfile(os.path.join(folder_path, f)) and is_supported_media(f)]
              
    return len(images)
