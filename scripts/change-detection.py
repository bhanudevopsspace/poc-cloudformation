#!/usr/bin/env python3
"""
Change Detection Script

Loads change-detection-config.yaml, diffs base vs head commits,
matches changed files against configured patterns, and generates
change-metadata.json with affected resources and deployment checklist.
"""

import json
import sys
import yaml
import fnmatch
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple


def load_change_detection_config(config_path: str) -> Dict[str, Any]:
    """Load YAML change detection configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_changed_files(base_commit: str = "main", head_commit: str = "HEAD") -> List[str]:
    """
    Get list of changed files between base and head commits.
    
    Args:
        base_commit: Base commit/branch reference
        head_commit: Head commit/branch reference (default: current HEAD)
    
    Returns:
        List of changed file paths
    """
    try:
        # Get diff between commits
        result = subprocess.run(
            ["git", "diff", "--name-only", base_commit, head_commit],
            capture_output=True,
            text=True,
            check=True
        )
        changed_files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
        return changed_files
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e}")
        # Fallback for placeholder/test scenarios
        return []


def is_excluded(file_path: str, exclusion_patterns: List[str]) -> bool:
    """Check if file matches any exclusion pattern."""
    normalized_path = file_path.replace("\\", "/")
    for pattern in exclusion_patterns:
        if fnmatch.fnmatch(normalized_path, pattern):
            return True
    return False


def match_file_to_mapping(file_path: str, resource_mappings: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Match a file to resource mappings.
    
    Returns:
        List of tuples (mapping_key, mapping_dict) for all matching patterns
    """
    normalized_path = file_path.replace("\\", "/")
    matches = []
    
    for mapping_key, mapping_config in resource_mappings.items():
        patterns = mapping_config.get('patterns', [])
        for pattern in patterns:
            if fnmatch.fnmatch(normalized_path, pattern):
                matches.append((mapping_key, mapping_config))
                break  # Only add once per mapping
    
    return matches


def run_change_detection(
    config_path: str = "config/change-detection-config.yaml",
    base_commit: str = "main",
    head_commit: str = "HEAD",
    output_path: str = "change-metadata.json"
) -> Dict[str, Any]:
    """
    Run change detection and generate metadata.
    
    Returns:
        Change metadata dictionary
    """
    
    # Load configuration
    config = load_change_detection_config(config_path)
    exclusion_patterns = config.get('exclusions', {}).get('patterns', [])
    resource_mappings = config.get('resourceMappings', {})
    deployment_checklist_config = config.get('deploymentChecklist', {})
    
    # Get changed files
    changed_files = get_changed_files(base_commit, head_commit)
    
    # Initialize metadata
    change_metadata = {
        "change_detection_config": config_path,
        "base_commit": base_commit,
        "head_commit": head_commit,
        "changed_files_count": len(changed_files),
        "changed_files": changed_files,
        "affected_resources": [],
        "affected_mappings": set(),  # Track which mappings were triggered
        "deployment_checklist": {key: False for key in deployment_checklist_config.keys()},
        "required_actions": set(),
        "cloudformation_conditions": {}
    }
    
    # Process each changed file
    for file_path in changed_files:
        # Skip excluded files
        if is_excluded(file_path, exclusion_patterns):
            continue
        
        # Match file to resource mappings
        matches = match_file_to_mapping(file_path, resource_mappings)
        
        for mapping_key, mapping_config in matches:
            # Add to affected resources
            change_metadata["affected_resources"].append({
                "file": file_path,
                "mapping": mapping_key,
                "resource_type": mapping_config.get('resource_type'),
                "impact_level": mapping_config.get('impact_level'),
                "target_stack": mapping_config.get('target_stack'),
                "description": mapping_config.get('description')
            })
            
            change_metadata["affected_mappings"].add(mapping_key)
            
            # Add required actions
            actions = mapping_config.get('required_actions', [])
            change_metadata["required_actions"].update(actions)
            
            # Update deployment checklist based on target_stack
            target_stack = mapping_config.get('target_stack')
            if target_stack == 'all':
                # Critical libraries affect all stacks
                for stack_key in change_metadata["deployment_checklist"].keys():
                    change_metadata["deployment_checklist"][stack_key] = True
            elif target_stack:
                change_metadata["deployment_checklist"][target_stack] = True
    
    # Convert sets to lists for JSON serialization
    change_metadata["affected_mappings"] = list(change_metadata["affected_mappings"])
    change_metadata["required_actions"] = list(change_metadata["required_actions"])
    
    # Write metadata to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(change_metadata, f, indent=2)
    
    print(f"Change detection complete. Metadata written to: {output_file}")
    print(f"Changed files: {len(changed_files)}")
    print(f"Affected resources: {len(change_metadata['affected_resources'])}")
    print(f"Deployment checklist: {change_metadata['deployment_checklist']}")
    print(f"Required actions: {change_metadata['required_actions']}")
    
    return change_metadata


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect changes and generate deployment metadata")
    parser.add_argument(
        "--config",
        default="config/change-detection-config.yaml",
        help="Path to change detection configuration"
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base commit/branch for comparison (default: main)"
    )
    parser.add_argument(
        "--head",
        default="HEAD",
        help="Head commit/branch for comparison (default: HEAD)"
    )
    parser.add_argument(
        "--output",
        default="change-metadata.json",
        help="Output path for change metadata JSON"
    )
    
    args = parser.parse_args()
    
    try:
        metadata = run_change_detection(
            config_path=args.config,
            base_commit=args.base,
            head_commit=args.head,
            output_path=args.output
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
