#!/usr/bin/env python3
"""
Analyze a Capella model and generate model-design-progress.json.
"""

import argparse
import json
import os
import subprocess
import sys


def get_git_info():
    """Get current git revision and commit hash."""
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True
        ).strip()
    except Exception:
        revision = os.environ.get("GITHUB_REF_NAME", "unknown")

    try:
        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True
        ).strip()[:12]
    except Exception:
        commit_hash = os.environ.get("GITHUB_SHA", "unknown")[:12]

    return revision, commit_hash


def analyze_with_capellambse(model_path):
    """Analyze model using py-capellambse library."""
    try:
        import capellambse
    except ImportError:
        print("Warning: capellambse not installed, using fallback analysis")
        return None

    try:
        model = capellambse.MelodyModel(model_path)

        layers = {}
        layer_mapping = {
            "OA": "operational_analysis",
            "SA": "system_analysis",
            "LA": "logical_architecture",
            "PA": "physical_architecture",
        }

        for layer_name, layer_attr in layer_mapping.items():
            try:
                layer = getattr(model, layer_attr, None)
                if layer is None:
                    layer = getattr(model, layer_name.lower(), None)

                if layer:
                    objects = len(list(layer.all_objects)) if hasattr(layer, 'all_objects') else 0
                    diagrams = len(list(layer.diagrams)) if hasattr(layer, 'diagrams') else 0

                    target_diagrams = 20
                    diagram_score = min(diagrams / target_diagrams, 1.0) if target_diagrams > 0 else 0.0

                    target_objects = 50
                    object_score = min(objects / target_objects, 1.0) if target_objects > 0 else 0.0

                    if objects > 0:
                        auto_score = 0.7 * diagram_score + 0.3 * object_score
                    else:
                        auto_score = diagram_score

                    layers[layer_name] = {
                        "auto_score": round(auto_score, 2),
                        "objects": objects,
                        "diagrams": diagrams,
                    }
                else:
                    layers[layer_name] = {
                        "auto_score": 0.0,
                        "objects": 0,
                        "diagrams": 0,
                    }
            except Exception as e:
                print(f"Warning: Error analyzing {layer_name}: {e}")
                layers[layer_name] = {
                    "auto_score": 0.0,
                    "objects": 0,
                    "diagrams": 0,
                }

        return layers

    except Exception as e:
        print(f"Error loading model with capellambse: {e}")
        return None


def analyze_fallback(model_path):
    """Fallback analysis when capellambse is not available."""
    print("Using fallback analysis (file-based heuristic)")

    file_size = os.path.getsize(model_path) if os.path.exists(model_path) else 0
    size_mb = file_size / (1024 * 1024)

    layers = {}
    for layer_name in ["OA", "SA", "LA", "PA"]:
        auto_score = min(size_mb / 10.0, 1.0)

        layers[layer_name] = {
            "auto_score": round(auto_score, 2),
            "objects": 0,
            "diagrams": 0,
        }

    return layers


def main():
    parser = argparse.ArgumentParser(description="Analyze Capella model")
    parser.add_argument("--input", required=True, help="Path to .aird file")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Model file not found: {args.input}")
        sys.exit(1)

    print(f"Analyzing model: {args.input}")

    revision, commit_hash = get_git_info()
    print(f"Revision: {revision}, Commit: {commit_hash}")

    layers = analyze_with_capellambse(args.input)
    if layers is None:
        layers = analyze_fallback(args.input)

    result = {
        "revision": revision,
        "commit_hash": commit_hash,
        "layers": layers,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Progress file generated: {args.output}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
