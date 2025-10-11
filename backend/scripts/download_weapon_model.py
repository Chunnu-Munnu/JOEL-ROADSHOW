"""
Download pre-trained weapon detection model
"""

import os
import urllib.request
from pathlib import Path

def download_weapon_model():
    """Download YOLOv8 weapon detection model"""
    
    models_dir = Path(__file__).parent.parent / 'models'
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / 'weapon_yolov8.pt'
    
    if model_path.exists():
        print(f"✅ Weapon model already exists: {model_path}")
        return
    
    print("📥 Downloading weapon detection model...")
    print("   Source: GitHub - OD-WeaponDetection")
    
    # Option 1: Pre-trained model from GitHub
    url = "https://github.com/ari-dasci/OD-WeaponDetection/releases/download/v1.0/best.pt"
    
    try:
        urllib.request.urlretrieve(url, model_path)
        print(f"✅ Downloaded: {model_path}")
        print("\n🎯 Weapon detection model ready!")
        print("   Detected classes: pistol, rifle, knife\n")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("\n⚠️  Alternative options:")
        print("1. Download manually from:")
        print("   https://github.com/ari-dasci/OD-WeaponDetection/releases")
        print("2. Use Roboflow (requires API key):")
        print("   https://universe.roboflow.com/weapon-detection/weapon-detection-gxgw5")
        print("3. Comment out weapon detection in yolo_detector.py for demo\n")

if __name__ == "__main__":
    download_weapon_model()