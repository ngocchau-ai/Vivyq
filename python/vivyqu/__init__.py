"""
VivyQu: Quantum-Inspired Cognitive Engine & Decision Core
=========================================================
Kiến trúc 4 thành phần nhận thức của Vivy:
- Mắt (Eyes): WorldSensoryFeed, VivyquEyes
- Tai (Ears): AcousticSemanticFeed, VivyquEars
- Tay (Hands): ExecutionReceipt, VivyquHands
- Bộ nhớ (Memory): Episode, EpisodicMemoryBuffer
- Codecs: InputSplittingCodec, OutputStitchingCodec, StructuredAction
"""

from .engine import VivyquEngine
from .shm_client import VivyquShmClient
from .watchdog import WatchdogSupervisor, CircuitState, IncidentLevel, FlightRecorder
from .cautreo_dispatcher import CautreoDispatcher
from .codec import InputSplittingCodec, OutputStitchingCodec, StructuredAction
from .eyes import VivyquEyes, WorldSensoryFeed
from .ears import VivyquEars, AcousticSemanticFeed
from .hands import VivyquHands, ExecutionReceipt
from .memory import EpisodicMemoryBuffer, Episode
from .cautreo_harmonizer import HarmonizedCautreoBridge, HarmonizedDecision
from .types import (
    DecisionResult,
    VivyquInputFrame,
    VivyquOutputFrame,
    CL12_DIMENSION,
    CONSTRAINT_MASK_BYTES,
    MAX_ACTIVE_ROTORS,
)

__version__ = "1.2.0"
__all__ = [
    "VivyquEngine",
    "VivyquShmClient",
    "WatchdogSupervisor",
    "CircuitState",
    "IncidentLevel",
    "FlightRecorder",
    "CautreoDispatcher",
    "HarmonizedCautreoBridge",
    "HarmonizedDecision",
    "InputSplittingCodec",
    "OutputStitchingCodec",
    "StructuredAction",
    "VivyquEyes",
    "WorldSensoryFeed",
    "VivyquEars",
    "AcousticSemanticFeed",
    "VivyquHands",
    "ExecutionReceipt",
    "EpisodicMemoryBuffer",
    "Episode",
    "DecisionResult",
    "VivyquInputFrame",
    "VivyquOutputFrame",
    "CL12_DIMENSION",
    "CONSTRAINT_MASK_BYTES",
    "MAX_ACTIVE_ROTORS",
]
