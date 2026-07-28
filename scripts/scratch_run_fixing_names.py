import os
import sys

# Aggiunge il path del progetto per gli import
project_path = r"c:\Users\david\Desktop\to organize\photoalbum_orderer"
if project_path not in sys.path:
    sys.path.append(project_path)

from core.scanner import find_image_folders
from core.image_processor import process_folder
from core.hash_processor import process_perceptual_hash
from core.logger import setup_logger

def main():
    logger = setup_logger(project_path)
    logger.info("Avvio script di processamento manuale per Fixing_names")
    
    target_path = r"C:\Users\david\Desktop\to organize\Fixing_names"
    if not os.path.exists(target_path):
        logger.error(f"La directory specificata non esiste: {target_path}")
        return
        
    folders = find_image_folders(target_path)
    logger.info(f"Trovate {len(folders)} cartelle contenenti media da elaborare.")
    
    for idx, folder in enumerate(folders, 1):
        logger.info(f"[{idx}/{len(folders)}] Elaborazione cartella: {folder}")
        try:
            # 1. Elaborazione base (rinomina e allineamento)
            num_processed_base = process_folder(folder)
            logger.info(f"  -> Rinominati/allineati {num_processed_base} file multimediali.")
            
            # 2. Calcolo hash ed estrazione feature AI (con force=True)
            num_processed_hash = process_perceptual_hash(folder, force=True)
            logger.info(f"  -> Processati {num_processed_hash} hash/features AI (forzato).")
        except Exception as e:
            logger.error(f"  -> [ERRORE] Errore durante l'elaborazione di {folder}: {e}", exc_info=True)

if __name__ == "__main__":
    main()
