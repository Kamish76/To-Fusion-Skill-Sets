"""Shared CAD primitives, hardware generators, client utilities, and kinematic animation helpers for To-Fusion CAD skills."""
from .cad_primitives import cm, mm, make_hex_points, set_user_param
from .fusion_client import execute_api_script, get_screenshot
from .hardware_library import (
    generate_din_7991_screw,
    generate_din_934_nut,
    generate_makers_supply_m3_joint_stackup,
)
from .scene_animator import (
    clamp,
    smoothstep,
    make_yz_transform,
    check_stage_interference,
    compile_ping_pong_gif,
    compile_ping_pong_gif_powershell,
)

__all__ = [
    "cm",
    "mm",
    "make_hex_points",
    "set_user_param",
    "execute_api_script",
    "get_screenshot",
    "generate_din_7991_screw",
    "generate_din_934_nut",
    "generate_makers_supply_m3_joint_stackup",
    "clamp",
    "smoothstep",
    "make_yz_transform",
    "check_stage_interference",
    "compile_ping_pong_gif",
    "compile_ping_pong_gif_powershell",
]
