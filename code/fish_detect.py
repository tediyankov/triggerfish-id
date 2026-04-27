## code for running Olly's triggerfish classifier on iNaturalist images, cropping to the detected box, and saving the crops

from pathlib import Path
from PIL import Image
from ultralytics import RTDETR
import torch

## config
IMAGE_DIR = "/gws/nopw/j04/iecdt/tyankov/triggerfish-id/data/inaturalist/Rhinecanthus_aculeatus_images"
OUTPUT_DIR = "/gws/nopw/j04/iecdt/tyankov/triggerfish-id/data/inaturalist_cropped/Rhinecanthus_aculeatus_images"
CHECKPOINT = "/gws/nopw/j04/iecdt/tyankov/triggerfish-id/models/RTDETR_aq_and_wild.pt"

CONF_THRESHOLD = 0.3  # minimum confidence to keep a detection
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

# setup
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
model = RTDETR(CHECKPOINT)
model.to(DEVICE)

image_paths = list(Path(IMAGE_DIR).glob("*.*"))
print(f"Found {len(image_paths)} images")

no_detection_count = 0

for img_path in image_paths:
    try:
        img = Image.open(img_path).convert("RGB")
        results = model(img, conf=CONF_THRESHOLD, verbose=False)

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            print(f"No detection: {img_path.name}")
            no_detection_count += 1
            continue

        # take the highest confidence box
        best_idx = boxes.conf.argmax().item()
        x1, y1, x2, y2 = boxes.xyxy[best_idx].tolist()

        # crop and save
        cropped = img.crop((x1, y1, x2, y2))
        save_path = Path(OUTPUT_DIR) / img_path.name
        cropped.save(save_path)

    except Exception as e:
        print(f"Error with {img_path.name}: {e}")

print(f"\nDone! Cropped images saved to {OUTPUT_DIR}")
print(f"Images with no detection: {no_detection_count}")