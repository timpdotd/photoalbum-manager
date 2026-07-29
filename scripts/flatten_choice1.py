import os
import re
from pathlib import Path

ROOT_DIR = r"D:\Photos\PhotoAlbum"
DRY_RUN = False

def run():
    print(f"Starting photo album flattener. DRY_RUN={DRY_RUN}")
    root_path = Path(ROOT_DIR)
    if not root_path.exists():
        print(f"Error: {ROOT_DIR} does not exist.")
        return

    # Regex to match the start of a year, e.g., 2025-01_Name, 2026-03_29_Name, 2019-05_Name
    # Group 1: Year (e.g. 2025)
    # Group 2: Month (optional, e.g. 01)
    # Group 3: Rest of the name
    date_regex = re.compile(r"^(\d{4})(?:-(\d{2}))?_?(.*)$")

    moves = []
    
    # We will traverse top-down. Once we find an event folder, we record it and DO NOT traverse inside it.
    for dirpath, dirnames, filenames in os.walk(root_path):
        current_dir = Path(dirpath)
        
        # We don't process the root dir itself for this check
        if current_dir == root_path:
            continue
            
        # Is this folder an event folder? (starts with Year)
        match = date_regex.match(current_dir.name)
        if match:
            year = match.group(1)
            month = match.group(2)
            rest = match.group(3)
            
            # Determine categories by looking at relative path from root
            rel_path = current_dir.relative_to(root_path)
            parts = list(rel_path.parts)
            
            # If the first part of the relative path is exactly a 4-digit year, this is already flattened. Skip it.
            if len(parts) > 0 and re.match(r"^\d{4}$", parts[0]):
                dirnames.clear()
                continue
                
            # The last part is the event folder itself
            event_folder = parts.pop()
            
            # Categories are the remaining parts. We deduplicate adjacent identical parts
            categories = []
            for p in parts:
                if not categories or categories[-1] != p:
                    categories.append(p)
                    
            # Build the new name
            date_prefix = f"{year}-{month}" if month else year
            
            # Form category string
            cat_string = " - ".join(categories)
            
            # Clean up rest (remove leading underscores/dashes)
            rest_clean = rest.lstrip("_-")
            
            # Construct new leaf name
            new_name = f"{date_prefix}"
            if cat_string:
                new_name += f" - {cat_string}"
            if rest_clean:
                new_name += f" - {rest_clean}"
                
            new_dest_dir = root_path / year / new_name
            
            moves.append((current_dir, new_dest_dir))
            
            # Prevent os.walk from going deeper into this event folder
            dirnames.clear()
            
    # Now execute moves (or dry run)
    print(f"\nFound {len(moves)} event folders to move.")
    
    for src, dest in moves:
        print(f"MOVE:")
        print(f"  FROM: {src}")
        print(f"  TO:   {dest}")
        
        if not DRY_RUN:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Use os.rename for instant moving within the same drive
            os.rename(src, dest)
            
    if not DRY_RUN:
        print("\nCleaning up empty category folders...")
        # Bottom-up traversal to delete empty directories
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
            current_dir = Path(dirpath)
            if current_dir == root_path:
                continue
                
            # If the folder matches a 4-digit year exactly, we keep it
            if re.match(r"^\d{4}$", current_dir.name):
                continue
                
            try:
                if not any(current_dir.iterdir()):
                    current_dir.rmdir()
                    print(f"Deleted empty folder: {current_dir}")
            except Exception as e:
                pass
                
    print("\nDone!")

if __name__ == "__main__":
    run()
