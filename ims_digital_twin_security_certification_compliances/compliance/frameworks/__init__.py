"""Per-framework control definitions."""
from .uk_tsa import UK_TSA_CONTROLS
from .eu_ai_act import EU_AI_ACT_CONTROLS
from .iso_42001 import ISO_42001_CONTROLS
from .nist_ai_rmf import NIST_AI_RMF_CONTROLS
from .mit_ai_risk import MIT_AI_RISK_CONTROLS
from .oecd_ai import OECD_AI_CONTROLS

__all__ = [
    "UK_TSA_CONTROLS", "EU_AI_ACT_CONTROLS", "ISO_42001_CONTROLS",
    "NIST_AI_RMF_CONTROLS", "MIT_AI_RISK_CONTROLS", "OECD_AI_CONTROLS",
]
