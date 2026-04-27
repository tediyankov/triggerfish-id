
import torch
from pathlib import Path
from PIL import Image
from torchvision import transforms
import csv

from model import create_model_on_device

## config
IMAGE_DIR = "/gws/nopw/j04/iecdt/tyankov/triggerfish-id/data/inaturalist_cropped/Rhinecanthus_aculeatus_images"
CHECKPOINT = "/gws/nopw/j04/iecdt/tyankov/triggerfish-id/models/pose_classifier_FCN_concat_feats.pytorch"
OUTPUT_CSV = "/gws/nopw/j04/iecdt/tyankov/triggerfish-id/data/pose_predictions_cropped.csv"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CLASS_NAMES = ["anterior", "posterior", "dorsal", "lateral"]

MODEL_CONFIG = {
    "feature_type": "CONCAT",
    "num_classes": 4,
    "backbone": "vitb14",
}

## loading model
model = create_model_on_device(DEVICE, MODEL_CONFIG)

ckpt = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)

state_dict = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt

# remap keys: "linear_head.X" -> "linear_head.linear_head.X"
remapped = {}
for k, v in state_dict.items():
    if k.startswith("linear_head."):
        new_k = "linear_head.linear_head." + k[len("linear_head."):]
        remapped[new_k] = v
    else:
        remapped[k] = v

model.load_state_dict(remapped, strict=False)

model.eval()

# transforming
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# getting images
image_paths = list(Path(IMAGE_DIR).glob("*.*"))

# opening CSV
with open(OUTPUT_CSV, mode="w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["image_name", "pose_label"])  # header

    # inference loop!!
    for img_path in image_paths:
        try:
            img = Image.open(img_path).convert("RGB")
            x = transform(img).unsqueeze(0).to(DEVICE)

            with torch.no_grad():
                logits = model(x)
                pred = logits.argmax(dim=1).item()

            pose_label = CLASS_NAMES[pred]

            writer.writerow([img_path.name, pose_label])

        except Exception as e:
            print(f"Error with {img_path}: {e}")

print(f"Saved results to {OUTPUT_CSV}")