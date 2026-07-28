import os
import csv
import shutil
from PySide6.QtGui import QImage, QTransform
from PySide6.QtCore import Qt
from core.logger import get_logger

def execute_save(pending_actions):
    """
    Esegue le azioni pendenti. pending_actions è un dizionario
    con chiave il percorso assoluto del file.
    """
    folders_to_update = {}
    
    # 1. Processa file fisici
    for file_path, actions in pending_actions.items():
        folder_path = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        if folder_path not in folders_to_update:
            folders_to_update[folder_path] = {}
        folders_to_update[folder_path][filename] = actions
        
        # Ignora se il file non esiste
        if not os.path.exists(file_path):
            continue

        # Se eliminato, ignora le altre operazioni e cancella
        if actions.get("deleted", False):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                # Elimina anche dalla cartella Printed se presente
                printed_path = os.path.join(folder_path, "Printed", filename)
                if os.path.exists(printed_path):
                    os.remove(printed_path)
                    
                # Elimina la feature se presente
                base_name = os.path.splitext(filename)[0]
                feat_path = os.path.join(folder_path, "Features", f"{base_name}.npy")
                if os.path.exists(feat_path):
                    os.remove(feat_path)
                    
            except Exception as e:
                get_logger().error(f"Errore eliminazione {filename}: {e}")
            continue

        # Rotazione (salta per i video)
        from core.scanner import is_video_file
        rotation = actions.get("rotation", 0) % 360
        if rotation != 0 and not is_video_file(filename):
            img = QImage(file_path)
            if not img.isNull():
                transform = QTransform().rotate(rotation)
                img = img.transformed(transform, Qt.SmoothTransformation)
                img.save(file_path)
                
        # Stampato (copia in cartella Printed)
        if actions.get("printed", False):
            printed_folder = os.path.join(folder_path, "Printed")
            os.makedirs(printed_folder, exist_ok=True)
            dest_path = os.path.join(printed_folder, filename)
            if not os.path.exists(dest_path):
                try:
                    from core.image_processor import get_file_timestamps, restore_file_timestamps
                    ts = get_file_timestamps(file_path)
                    shutil.copy2(file_path, dest_path)
                    restore_file_timestamps(dest_path, ts)
                except Exception as e:
                    get_logger().error(f"Errore copia {filename}: {e}")

    # 2. Aggiorna CSV per ogni cartella toccata
    for folder_path, actions_in_folder in folders_to_update.items():
        update_csv(folder_path, actions_in_folder)
        # Esegui la rinomina e numerazione sequenziale per sistemare eventuali buchi causati da eliminazioni/spostamenti
        from core.image_processor import rename_files_chronologically
        rename_files_chronologically(folder_path)

def update_csv(folder_path, pending_actions=None):
    if pending_actions is None:
        pending_actions = {}
        
    folder_name = os.path.basename(os.path.normpath(folder_path))
    if not folder_name:
        folder_name = "images"
        
    csv_path = os.path.join(folder_path, f"{folder_name}.csv")
    
    rows = []
    existing_files = set()
    headers = []
    
    # Leggi esistente se c'è
    if os.path.exists(csv_path):
        with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            try:
                headers = next(reader)
            except StopIteration:
                headers = ["Filename", "Printed", "PerceptualHash", "ColorHist", "AI_Feat"]
            
            if "Printed" not in headers: headers.append("Printed")
            if "PerceptualHash" not in headers: headers.append("PerceptualHash")
            if "ColorHist" not in headers: headers.append("ColorHist")
            if "AI_Feat" not in headers: headers.append("AI_Feat")
                
            printed_idx = headers.index("Printed")
            hash_idx = headers.index("PerceptualHash")
            ai_idx = headers.index("AI_Feat")
            filename_idx = headers.index("Filename") if "Filename" in headers else 0
            
            rows.append(headers)
            
            for row in reader:
                if not row:
                    continue
                    
                fname = row[filename_idx]
                
                # Se è segnato come eliminato, saltiamo la riga
                if fname in pending_actions and pending_actions[fname].get("deleted", False):
                    continue
                    
                # Se il file non esiste più fisicamente (eliminato manualmente), pulisci il CSV
                if not os.path.exists(os.path.join(folder_path, fname)):
                    continue
                    
                # Espandi la riga se mancano colonne
                while len(row) <= max(printed_idx, hash_idx, ai_idx):
                    row.append("")
                    
                # Inizializza i valori vuoti per Printed
                if not row[printed_idx]: row[printed_idx] = "False"
                    
                # Aggiorna se marcato printed nei pending actions
                if fname in pending_actions and pending_actions[fname].get("printed", False):
                    row[printed_idx] = "True"
                    
                existing_files.add(fname)
                rows.append(row)
    else:
        # Crea nuovo
        headers = ["Filename", "Printed", "PerceptualHash", "ColorHist", "AI_Feat"]
        rows.append(headers)

    # Aggiungi i file NUOVI trovati fisicamente nella cartella
    try:
        from core.scanner import is_supported_media
        physical_files = [f for f in os.listdir(folder_path) 
                          if os.path.isfile(os.path.join(folder_path, f)) and is_supported_media(f)]
                          
        printed_idx = headers.index("Printed") if "Printed" in headers else 1
        filename_idx = headers.index("Filename") if "Filename" in headers else 0
        
        for img in physical_files:
            if img in existing_files:
                continue
                
            if img in pending_actions and pending_actions[img].get("deleted", False):
                continue
                
            printed = "True" if (img in pending_actions and pending_actions[img].get("printed", False)) else "False"
            
            new_row = [""] * len(headers)
            new_row[filename_idx] = img
            new_row[printed_idx] = printed
            
            rows.append(new_row)
            
    except Exception as e:
        get_logger().error(f"Errore aggiunta nuovi file in {folder_path}: {e}")

    # Scrivi il CSV aggiornato
    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

def move_media_files(file_paths, dest_folder):
    """
    Sposta fisicamente i file multimediali in dest_folder.
    Gestisce anche la copia corrispondente in 'Printed' e 'Features' se esistono.
    Pulisce i CSV delle cartelle di provenienza e aggiorna quello di destinazione.
    """
    import shutil
    from core.logger import get_logger
    
    logger = get_logger()
    os.makedirs(dest_folder, exist_ok=True)
    
    # Raggruppa i file da rimuovere per cartella di origine
    sources_to_update = {} # {src_dir: {filename: {"deleted": True}}}
    
    moved_count = 0
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            continue
            
        src_dir = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        dest_path = os.path.join(dest_folder, filename)
        
        # Se il file esiste già a destinazione, risolviamo il conflitto aggiungendo un suffisso
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(os.path.join(dest_folder, f"{base}_{counter}{ext}")):
                counter += 1
            dest_filename = f"{base}_{counter}{ext}"
            dest_path = os.path.join(dest_folder, dest_filename)
        else:
            dest_filename = filename
            
        try:
            from core.image_processor import get_file_timestamps, restore_file_timestamps
            src_ts = get_file_timestamps(file_path)
            
            src_printed = os.path.join(src_dir, "Printed", filename)
            printed_ts = get_file_timestamps(src_printed) if os.path.exists(src_printed) else None
            
            # Sposta il file multimediale principale
            shutil.move(file_path, dest_path)
            restore_file_timestamps(dest_path, src_ts)
            
            # Gestisci il file "Printed" se esiste
            if os.path.exists(src_printed):
                dest_printed_dir = os.path.join(dest_folder, "Printed")
                os.makedirs(dest_printed_dir, exist_ok=True)
                dest_printed_path = os.path.join(dest_printed_dir, dest_filename)
                shutil.move(src_printed, dest_printed_path)
                restore_file_timestamps(dest_printed_path, printed_ts)
                
            # Gestisci il file "Features" se esiste
            base_name = os.path.splitext(filename)[0]
            dest_base_name = os.path.splitext(dest_filename)[0]
            src_feat = os.path.join(src_dir, "Features", f"{base_name}.npy")
            if os.path.exists(src_feat):
                dest_feat_dir = os.path.join(dest_folder, "Features")
                os.makedirs(dest_feat_dir, exist_ok=True)
                dest_feat_path = os.path.join(dest_feat_dir, f"{dest_base_name}.npy")
                shutil.move(src_feat, dest_feat_path)
                
            # Registra l'azione per aggiornare il CSV di provenienza
            if src_dir not in sources_to_update:
                sources_to_update[src_dir] = {}
            sources_to_update[src_dir][filename] = {"deleted": True}
            
            moved_count += 1
        except Exception as e:
            logger.error(f"Errore nello spostamento di {filename} in {dest_folder}: {e}")
            
    # Aggiorna il CSV per ciascuna cartella di provenienza toccata
    for src_dir, actions in sources_to_update.items():
        update_csv(src_dir, actions)
        from core.image_processor import rename_files_chronologically
        rename_files_chronologically(src_dir)
        
    # Aggiorna il CSV della cartella di destinazione
    if moved_count > 0:
        update_csv(dest_folder)
        from core.image_processor import rename_files_chronologically
        rename_files_chronologically(dest_folder)
        
    return moved_count

