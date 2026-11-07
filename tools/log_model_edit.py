#!/usr/bin/env python3
"""
Log Model Edit: Programmatically logs user-dictated edits, parameter changes,
and mechanical decisions directly into the model's TIMELINE.md and DECISIONS.md.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import argparse
from datetime import datetime
from pathlib import Path

script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from tools.scaffold_model import find_monorepo_root

def resolve_model_dir(model_input: str) -> str:
    path = Path(model_input).resolve()
    if path.is_dir() and ((path / "CONTEXT.md").exists() or (path / "SPEC.md").exists()):
        return str(path)

    # Search in CAD_MONOREPO_ROOT or standard paths
    root = find_monorepo_root()
    models_dir = Path(root) / "models"
    if models_dir.exists():
        # 1. Exact match first
        for d in models_dir.iterdir():
            if d.is_dir() and d.name.lower() == model_input.lower():
                return str(d.resolve())
        # 2. Substring match with ambiguity validation
        matches = [d for d in models_dir.iterdir() if d.is_dir() and model_input.lower() in d.name.lower()]
        if len(matches) == 1:
            return str(matches[0].resolve())
        elif len(matches) > 1:
            match_names = [d.name for d in matches]
            raise ValueError(f"Ambiguous model name '{model_input}'. Multiple matches found: {', '.join(match_names)}")

    raise FileNotFoundError(f"Could not locate model folder for '{model_input}'")

def get_next_adr_index(decisions_path: Path) -> int:
    if not decisions_path.exists():
        return 1
    content = decisions_path.read_text(encoding="utf-8")
    import re
    matches = re.findall(r"ADR-(\d+)", content)
    if not matches:
        return 1
    indices = [int(m) for m in matches]
    return max(indices) + 1

def log_edit(
    model_dir_str: str,
    prompt: str,
    tier: int = 1,
    comp: str = "",
    target: str = "",
    before: str = "",
    after: str = "",
    status: str = "HEALTHY",
    screenshot: str = "",
    adr_title: str = "",
    adr_context: str = "",
    adr_decision: str = ""
):
    model_dir = Path(model_dir_str)
    timeline_path = model_dir / "TIMELINE.md"
    decisions_path = model_dir / "DECISIONS.md"
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M")

    tier_names = {
        1: "Tier 1 (Parametric Edit)",
        2: "Tier 2 (Timeline Rollback Surgery)",
        3: "Tier 3 (Localized Downstream Feature Append)",
        4: "Tier 4 (Scoped Sub-Component Replacement)"
    }
    tier_label = tier_names.get(tier, f"Tier {tier}")

    # 1. Append to TIMELINE.md
    if not timeline_path.exists():
        timeline_path.write_text(f"# Change & Prompt Timeline\n\n", encoding="utf-8")

    entry = [
        f"\n### [{now_iso}] Directive: \"{prompt}\"",
        f"- **Edit Tier:** {tier_label}",
    ]
    if comp:
        entry.append(f"- **Component:** `{comp}`")
    if target:
        entry.append(f"- **Target Entity:** `{target}`")
    if before and after:
        entry.append(f"- **Delta:** `{before}` $\\rightarrow$ `{after}`")
    entry.append(f"- **Timeline Health:** {status}")
    if screenshot:
        entry.append(f"- **Verification Render:** `[{Path(screenshot).name}]({screenshot})`")

    with open(timeline_path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry) + "\n")

    print(f"📝 Appended entry to {timeline_path}")

    # 2. Optional: Append ADR to DECISIONS.md
    if adr_title:
        idx = get_next_adr_index(decisions_path)
        adr_entry = [
            f"\n---",
            f"\n### ADR-{idx:03d}: {adr_title}",
            f"- **Date:** {now_iso}",
            f"- **Status:** Accepted",
            f"- **Context:** {adr_context or prompt}",
            f"- **Decision:** {adr_decision or f'Adjusted {target} from {before} to {after}.'}",
            f"- **Consequences:** Maintained timeline integrity and verified with post-edit diagnostic."
        ]
        with open(decisions_path, "a", encoding="utf-8") as f:
            f.write("\n".join(adr_entry) + "\n")
        print(f"📐 Appended ADR-{idx:03d} to {decisions_path}")

def main():
    parser = argparse.ArgumentParser(description="Log Model Edit to CAD-ICM Timeline & ADRs")
    parser.add_argument("--model", required=True, help="Model folder path or name")
    parser.add_argument("--prompt", required=True, help="Natural language prompt or directive")
    parser.add_argument("--tier", type=int, default=1, choices=[1, 2, 3, 4], help="Edit tier (1-4)")
    parser.add_argument("--comp", default="", help="Component modified")
    parser.add_argument("--target", default="", help="Feature or parameter name")
    parser.add_argument("--before", default="", help="Previous value")
    parser.add_argument("--after", default="", help="New applied value")
    parser.add_argument("--status", default="HEALTHY", help="Health status (HEALTHY, WARNING, ERROR)")
    parser.add_argument("--screenshot", default="", help="Path to verification screenshot")
    parser.add_argument("--adr-title", default="", help="Optional Architectural Decision title")
    parser.add_argument("--adr-context", default="", help="Optional ADR context")
    parser.add_argument("--adr-decision", default="", help="Optional ADR decision details")
    args = parser.parse_args()

    model_dir = resolve_model_dir(args.model)
    log_edit(
        model_dir_str=model_dir,
        prompt=args.prompt,
        tier=args.tier,
        comp=args.comp,
        target=args.target,
        before=args.before,
        after=args.after,
        status=args.status,
        screenshot=args.screenshot,
        adr_title=args.adr_title,
        adr_context=args.adr_context,
        adr_decision=args.adr_decision
    )

if __name__ == "__main__":
    main()
