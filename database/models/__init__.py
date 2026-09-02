"""
Database Models Package Registry
"""

from database.models.base import BaseModel
from database.models.auth import User
from database.models.session import UserSession
from database.models.security_policy import SecurityPolicy
from database.models.audit import AuditLog
from database.models.activity import UserActivityEvent
from database.models.runtime_config import SystemRuntimeConfig
from database.models.vehicle_hierarchy import (
    ProductFamily,
    Vehicle,
    VehicleModel,
    VehicleVariant,
    ModelGeneration,
    ModelYear,
)
from database.models.part_bom import (
    Subsystem,
    Assembly,
    Component,
    Material,
    Supplier,
    Part,
    BomItem,
    ComponentCost,
)
from database.models.plant_opex import (
    Plant,
    ProductionRecord,
    OpexRecord,
    BenchmarkRecord,
)
from database.models.engineering_change import (
    EngineeringChange,
    Implementation,
)
from database.models.ideathon import (
    IdeaSubmission,
    IdeaCluster,
    IdeaDuplicateLink,
    IdeaDecisionState,
    ImplementationEvidenceState,
    DataQualityStatus,
    CostReductionCategory,
    OpportunityStatus,
    IdeaOpportunityEvaluation,
)
from database.models.governance import (
    ReviewStatus,
    ReviewPriority,
    ReviewActionType,
    ConfidenceTier,
    IdeaReviewRecord,
    IdeaReviewAction,
)
from database.models.embeddings import RecordEmbedding

__all__ = [
    "BaseModel",
    "User",
    "UserSession",
    "SecurityPolicy",
    "AuditLog",
    "UserActivityEvent",
    "SystemRuntimeConfig",
    "ProductFamily",
    "Vehicle",
    "VehicleModel",
    "VehicleVariant",
    "ModelGeneration",
    "ModelYear",
    "Subsystem",
    "Assembly",
    "Component",
    "Material",
    "Supplier",
    "Part",
    "BomItem",
    "ComponentCost",
    "Plant",
    "ProductionRecord",
    "OpexRecord",
    "BenchmarkRecord",
    "EngineeringChange",
    "Implementation",
    "IdeaSubmission",
    "IdeaCluster",
    "IdeaDuplicateLink",
    "IdeaDecisionState",
    "ImplementationEvidenceState",
    "DataQualityStatus",
    "CostReductionCategory",
    "OpportunityStatus",
    "IdeaOpportunityEvaluation",
    "ReviewStatus",
    "ReviewPriority",
    "ReviewActionType",
    "ConfidenceTier",
    "IdeaReviewRecord",
    "IdeaReviewAction",
    "RecordEmbedding",
]
