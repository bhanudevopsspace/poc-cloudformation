#!/usr/bin/env python3
"""
Prepare Change Metadata Script

Takes change-metadata.json and decorates it with CloudFormation condition flags
derived from the deployment checklist, producing an enhanced metadata file for
templated conditional deployments.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def load_change_metadata(metadata_path: str) -> Dict[str, Any]:
    """Load change metadata JSON file."""
    with open(metadata_path, 'r') as f:
        return json.load(f)


def load_condition_mapping(config_path: str = "config/change-detection-config.yaml") -> Dict[str, str]:
    """Load CloudFormation condition mapping from config."""
    import yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('cloudFormationConditionMapping', {})


def prepare_change_metadata(
    metadata_path: str = "change-metadata.json",
    config_path: str = "config/change-detection-config.yaml",
    output_path: str = "change-metadata-enhanced.json"
) -> Dict[str, Any]:
    """
    Enhance change metadata with CloudFormation condition flags.
    
    Args:
        metadata_path: Path to input change-metadata.json
        config_path: Path to change-detection-config.yaml
        output_path: Path to output enhanced metadata
    
    Returns:
        Enhanced metadata dictionary
    """
    
    # Load inputs
    metadata = load_change_metadata(metadata_path)
    condition_mapping = load_condition_mapping(config_path)
    
    # Build CloudFormation conditions based on deployment checklist
    cloudformation_conditions = {}
    deployment_checklist = metadata.get("deployment_checklist", {})
    
    for checklist_key, should_deploy in deployment_checklist.items():
        cf_condition = condition_mapping.get(checklist_key)
        if cf_condition:
            cloudformation_conditions[cf_condition] = should_deploy
    
    # Add special composite conditions
    # Deploy application stack if either application1 or application2 changed
    if "application" in deployment_checklist:
        cloudformation_conditions["DeployApplicationStack"] = deployment_checklist.get("application", False)
    
    # Enhanced metadata
    enhanced_metadata = metadata.copy()
    enhanced_metadata["cloudformation_conditions"] = cloudformation_conditions
    enhanced_metadata["metadata_version"] = "2.0"
    enhanced_metadata["enhanced"] = True
    
    # Add computed fields for decision-making
    enhanced_metadata["has_affected_resources"] = len(metadata.get("affected_resources", [])) > 0
    enhanced_metadata["has_deployments"] = any(deployment_checklist.values())
    enhanced_metadata["is_valid"] = enhanced_metadata["has_affected_resources"] and enhanced_metadata["has_deployments"]
    
    # Write enhanced metadata to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(enhanced_metadata, f, indent=2)
    
    print(f"Change metadata enhanced. Written to: {output_file}")
    print(f"CloudFormation conditions: {cloudformation_conditions}")
    print(f"Valid for deployment: {enhanced_metadata['is_valid']}")
    
    return enhanced_metadata


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance change metadata with CloudFormation conditions")
    parser.add_argument(
        "--metadata",
        default="change-metadata.json",
        help="Path to input change metadata JSON"
    )
    parser.add_argument(
        "--config",
        default="config/change-detection-config.yaml",
        help="Path to change detection configuration"
    )
    parser.add_argument(
        "--output",
        default="change-metadata-enhanced.json",
        help="Output path for enhanced metadata JSON"
    )
    
    args = parser.parse_args()
    
    try:
        metadata = prepare_change_metadata(
            metadata_path=args.metadata,
            config_path=args.config,
            output_path=args.output
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
