from enum import Enum
import logging
from typing import Union
import torch

import torch.nn as nn

class FeatureType(Enum):
    NO_CONCAT = 768
    CONCAT = 1536

class LinearHead(nn.Module):
    def __init__(self, *, num_classes = 5, feat_type: FeatureType = FeatureType['NO_CONCAT']):
        super().__init__()
        self.num_classes = num_classes
        self.feat_type = feat_type
        self.embed_dim = feat_type.value
        self.hidden_dim = max(1, self.embed_dim // 2)
        self.linear_head = nn.Sequential(
            nn.Linear(in_features=self.embed_dim, out_features=self.hidden_dim, bias=True),
            nn.GELU(),
            nn.Dropout(p=0.2, inplace=False),
            nn.Linear(in_features=self.hidden_dim, out_features=self.num_classes, bias=True),
        )
        
    def forward(self, x):
        return self.linear_head(x)
    
class DINOClassifier(nn.Module):
    def __init__(self, *, backbone: nn.Module, linear_head: nn.Module):
        super().__init__()
        self.backbone = backbone
        self.linear_head = linear_head
        self.feat_type = linear_head.feat_type

    def forward(self, x):
        if self.feat_type == FeatureType['CONCAT']:
            x = self.backbone.forward_features(x)
            cls_token = x["x_norm_clstoken"]
            patch_tokens = x["x_norm_patchtokens"]
            linear_input = torch.cat([
                cls_token,
                patch_tokens.mean(dim=1),
            ], dim=1)
        elif self.feat_type == FeatureType['NO_CONCAT']:
            x = self.backbone.forward_features(x)
            linear_input = x["x_norm_clstoken"]
        else:
            raise ValueError(f"Unsupported feat_type: {self.feat_type.name!r}. Expected {FeatureType._member_names_}.")
        return self.linear_head(linear_input)

def create_model_on_device(
    device: str,
    model_struc_dict: dict,
    pretrained=False,
    distributed=False,
) -> torch.nn.Module:
    """
    Create a model on the specified device.

    Args:
        device (str): The device to create the model on (e.g., "cuda", "cpu").
        model_struc_dict (dict): A dictionary containing the model structure information.
        pretrained (bool): Whether to load pretrained weights for the model.
        distributed (bool): Whether to distribute training across multiple GPUs.

    Returns:
        torch.nn.Module: The created model.
    """
    feat_type = FeatureType[model_struc_dict['feature_type']]
    head = LinearHead(num_classes = model_struc_dict['num_classes'], feat_type = feat_type)
    backbone = torch.hub.load("facebookresearch/dinov2", f"dinov2_{model_struc_dict['backbone']}")
    model = DINOClassifier(backbone=backbone, linear_head=head)
    return model.to(device)
