"""
Download weapon detection model from GitHub
"""

import os
import urllib.request
from pathlib import Path

def download_weapon_model():
    """Download YOLOv8 weapon detection model from OD-WeaponDetection"""
    
    models_dir = Path(__file__).parent.parent / 'models'
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / 'weapon_yolov8.pt'
    
    if model_path.exists():
        print(f"✅ Weapon model already exists: {model_path}")
        return str(model_path)
    
    print("📥 Downloading weapon detection model...")
    print("   Source: GitHub - ari-dasci/OD-WeaponDetection")
    
    # Direct link to best.pt from releases
    url = "https://github.com/ari-dasci/OD-WeaponDetection/releases/download/v1.0/best.pt"
    
    try:
        print("   Downloading... (this may take a minute)")
        urllib.request.urlretrieve(url, model_path)
        print(f"✅ Downloaded: {model_path}")
        print("\n🎯 Weapon detection model ready!")
        print("   Classes: pistol, rifle, knife, grenade")
        print("   Model: YOLOv8 fine-tuned on 3000+ weapon images\n")
        return str(model_path)
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("\n⚠️  Manual download:")
        print("1. Visit: https://github.com/ari-dasci/OD-WeaponDetection/releases")
        print("2. Download 'best.pt'")
        print(f"3. Save to: {model_path}\n")
        return None

if __name__ == "__main__":
    download_weapon_model()