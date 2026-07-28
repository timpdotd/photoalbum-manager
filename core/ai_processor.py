import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import base64

class AIProcessor:
    def __init__(self):
        # Utilizziamo la GPU se disponibile (CUDA), altrimenti CPU
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Carichiamo EfficientNet-B0 pre-addestrata su ImageNet
        # Essendo una rete compatta e moderna, è ideale per prestazioni ottimali.
        self.model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        
        # Rimuoviamo l'ultimo layer di classificazione per ottenere le features pure (1280 dimensioni)
        self.model.classifier = torch.nn.Identity()
        self.model.eval()
        self.model.to(self.device)
        
        # Trasformazioni richieste da ImageNet
        self.preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
    def extract_features(self, image_or_path):
        """
        Estrae un vettore di 1280 features semantiche da un'immagine PIL o da un percorso file.
        Restituisce un array numpy 1D di float16.
        """
        try:
            if isinstance(image_or_path, Image.Image):
                img = image_or_path.convert('RGB')
            else:
                img = Image.open(image_or_path).convert('RGB')
            input_tensor = self.preprocess(img)
            input_batch = input_tensor.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                features = self.model(input_batch)
                
            # Convertiamo in numpy array e riduciamo la precisione a float16
            # per dimezzare lo spazio occupato nel CSV (da 5KB a 2.5KB per foto).
            feat_arr = features.squeeze().cpu().numpy().astype(np.float16)
            return feat_arr
        except Exception as e:
            print(f"Errore estrazione AI per {image_path}: {e}")
            return None
            
    def serialize_features(self, feat_arr):
        """Converte il numpy array in stringa base64 per il salvataggio su CSV"""
        if feat_arr is None:
            return ""
        return base64.b64encode(feat_arr.tobytes()).decode('utf-8')
        
    def deserialize_features(self, b64_str):
        """Decodifica la stringa base64 di ritorno in un array numpy float16"""
        if not b64_str:
            return None
        try:
            feat_bytes = base64.b64decode(b64_str)
            # Ricostruiamo l'array da 1280 dimensioni in float16
            feat_arr = np.frombuffer(feat_bytes, dtype=np.float16)
            return feat_arr
        except Exception:
            return None

# Singleton per evitare di caricare il modello in RAM più volte
_ai_processor_instance = None

def get_ai_processor():
    global _ai_processor_instance
    if _ai_processor_instance is None:
        _ai_processor_instance = AIProcessor()
    return _ai_processor_instance
