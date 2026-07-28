import torch
import torchvision.models as models
import cv2
import numpy as np

# Test EfficientNet
try:
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    model.classifier = torch.nn.Identity()
    model.eval()
    dummy_input = torch.randn(1, 3, 224, 224)
    out = model(dummy_input)
    print("EfficientNet-b0 output shape:", out.shape)
except Exception as e:
    print("EfficientNet Error:", e)

# Test HOG
try:
    img = np.zeros((64, 64), dtype=np.uint8)
    hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)
    feat = hog.compute(img)
    print("HOG feature shape:", feat.shape)
except Exception as e:
    print("HOG Error:", e)
