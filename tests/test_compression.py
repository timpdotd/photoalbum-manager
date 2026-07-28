import os
import shutil
from PIL import Image

def test_compression():
    base_dir = r"c:\Users\david\Desktop\to organize\photoalbum_orderer"
    test_folder = os.path.join(base_dir, "TEST", "FOLDER_1")
    output_folder = os.path.join(base_dir, "COMPRESSION_TEST")
    
    os.makedirs(output_folder, exist_ok=True)
    
    # Pick a couple of test images
    test_images = ["photo_0001.jpg", "photo_0005.jpg"]
    
    for img_name in test_images:
        img_path = os.path.join(test_folder, img_name)
        if not os.path.exists(img_path):
            print(f"Skipping {img_name}, not found.")
            continue
            
        print(f"\n--- Testing compression for {img_name} ---")
        
        # Original size
        orig_size = os.path.getsize(img_path)
        print(f"Original size: {orig_size / (1024*1024):.2f} MB")
        
        # Open image
        img = Image.open(img_path)
        base_name, _ = os.path.splitext(img_name)
        
        # 1. Stampa (Print Quality) - JPEG Quality 95, Optimized
        # Quasi nessuna perdita visiva, ma ottimizzato.
        out_print = os.path.join(output_folder, f"{base_name}_PRINT_q95.jpg")
        img.save(out_print, "JPEG", quality=95, optimize=True)
        size_print = os.path.getsize(out_print)
        print(f"1. PRINT (JPEG q=95, opt): {size_print / (1024*1024):.2f} MB ({(size_print/orig_size)*100:.1f}% of orig)")
        
        # 2. Archivio Alta Qualità - JPEG Quality 85, Optimized
        out_archive_hq = os.path.join(output_folder, f"{base_name}_ARCHIVE_HQ_q85.jpg")
        img.save(out_archive_hq, "JPEG", quality=85, optimize=True)
        size_archive_hq = os.path.getsize(out_archive_hq)
        print(f"2. ARCHIVE HQ (JPEG q=85, opt): {size_archive_hq / (1024*1024):.2f} MB ({(size_archive_hq/orig_size)*100:.1f}% of orig)")
        
        # 3. Archivio Standard - WebP Quality 85
        # Ottimo compromesso tra spazio e qualità visiva.
        out_webp = os.path.join(output_folder, f"{base_name}_ARCHIVE_WEBP_q85.webp")
        img.save(out_webp, "WEBP", quality=85)
        size_webp = os.path.getsize(out_webp)
        print(f"3. ARCHIVE WEBP (WEBP q=85): {size_webp / (1024*1024):.2f} MB ({(size_webp/orig_size)*100:.1f}% of orig)")
        
        # 4. Archivio Massimo - WebP Quality 75
        out_webp_max = os.path.join(output_folder, f"{base_name}_ARCHIVE_MAX_WEBP_q75.webp")
        img.save(out_webp_max, "WEBP", quality=75)
        size_webp_max = os.path.getsize(out_webp_max)
        print(f"4. ARCHIVE MAX (WEBP q=75): {size_webp_max / (1024*1024):.2f} MB ({(size_webp_max/orig_size)*100:.1f}% of orig)")

if __name__ == "__main__":
    test_compression()
