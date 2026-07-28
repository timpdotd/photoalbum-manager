import os

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

def is_supported_media(filename):
    """Controlla se un file è un'immagine o un video supportato."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_EXTENSIONS

def is_video_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS

def find_image_folders(root_path):
    """
    Attraversa la directory root_path e restituisce una lista di 
    percorsi di cartelle che contengono almeno un file multimediale.
    """
    media_folders = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Evita di cercare nella cartella "Printed" o cartelle nascoste
        dirnames[:] = [d for d in dirnames if d != "Printed" and not d.startswith('.')]
        
        has_media = any(is_supported_media(f) for f in filenames)
        if has_media:
            media_folders.append(dirpath)
            
    return media_folders
