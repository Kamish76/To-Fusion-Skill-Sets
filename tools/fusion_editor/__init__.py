"""
Fusion In-Place Editing Tool Suite
Provides fast, non-destructive, surgical CAD introspection, parameter editing,
timeline surgery, localized feature appending, and timeline health verification.
"""

from .inspect_model import inspect_fusion_model, generate_inspect_script
from .edit_parameter import edit_parameter_in_place, generate_param_edit_script
from .rollback_edit import rollback_and_edit, generate_rollback_script
from .append_feature import append_feature_in_place, generate_append_script
from .timeline_doctor import check_timeline_health, generate_health_script

__all__ = [
    "inspect_fusion_model",
    "generate_inspect_script",
    "edit_parameter_in_place",
    "generate_param_edit_script",
    "rollback_and_edit",
    "generate_rollback_script",
    "append_feature_in_place",
    "generate_append_script",
    "check_timeline_health",
    "generate_health_script",
]
