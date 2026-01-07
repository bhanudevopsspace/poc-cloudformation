#!/usr/bin/env python3
"""
Validate Change Impact Script

Sanity-checks the metadata to ensure there are affected resources and
a non-empty checklist when applicable. Fails fast if detection missed something.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_change_metadata(metadata_path: str) -> Dict[str, Any]:
    """Load change metadata JSON file."""
    with open(metadata_path, 'r') as f:
        return json.load(f)


def validate_change_impact(
    metadata_path: str = "change-metadata-enhanced.json",
    strict: bool = True
) -> tuple[bool, List[str], List[str]]:
    """
    Validate change impact metadata.
    
    Args:
        metadata_path: Path to metadata JSON file
        strict: If True, fail on any warnings; if False, only fail on errors
    
    Returns:
        Tuple of (is_valid: bool, errors: List[str], warnings: List[str])
    """
    
    metadata = load_change_metadata(metadata_path)
    errors = []
    warnings = []
    
    # Check 1: Ensure metadata has required fields
    if "affected_resources" not in metadata:
        errors.append("Metadata missing 'affected_resources' field")
    
    if "deployment_checklist" not in metadata:
        errors.append("Metadata missing 'deployment_checklist' field")
    
    # Early exit if structural errors
    if errors:
        return False, errors, warnings
    
    affected_resources = metadata.get("affected_resources", [])
    deployment_checklist = metadata.get("deployment_checklist", {})
    changed_files = metadata.get("changed_files", [])
    
    # Check 2: If files changed, should have affected resources
    if changed_files and len(changed_files) > 0:
        if not affected_resources or len(affected_resources) == 0:
            warnings.append(
                f"Files changed ({len(changed_files)}) but no affected resources identified. "
                "All changes may have been excluded."
            )
    
    # Check 3: If affected resources exist, deployment checklist should not be empty
    if affected_resources and len(affected_resources) > 0:
        if not any(deployment_checklist.values()):
            errors.append(
                f"Affected resources identified ({len(affected_resources)}) but deployment checklist is empty. "
                "This indicates a configuration error in change-detection-config.yaml"
            )
    
    # Check 4: Validate CloudFormation conditions exist if enhanced
    if metadata.get("enhanced"):
        cf_conditions = metadata.get("cloudformation_conditions", {})
        if not cf_conditions and affected_resources:
            warnings.append(
                "Enhanced metadata but no CloudFormation conditions generated. "
                "Template may not conditionally deploy resources."
            )
    
    # Check 5: Validate resource mapping consistency
    for resource in affected_resources:
        if "resource_type" not in resource:
            warnings.append(f"Resource missing 'resource_type': {resource.get('file', 'unknown')}")
        
        if "impact_level" not in resource:
            warnings.append(f"Resource missing 'impact_level': {resource.get('file', 'unknown')}")
    
    # Check 6: Ensure required actions are present for critical changes
    required_actions = metadata.get("required_actions", [])
    critical_resources = [r for r in affected_resources if r.get("impact_level") == "CRITICAL"]
    
    if critical_resources and not required_actions:
        errors.append(
            f"Found {len(critical_resources)} CRITICAL resources but no required actions defined. "
            "Build, test, or deployment steps may be missing."
        )
    
    # Determine if valid
    is_valid = len(errors) == 0 and (not strict or len(warnings) == 0)
    
    return is_valid, errors, warnings


def run_validation(
    metadata_path: str = "change-metadata-enhanced.json",
    strict: bool = False,
    exit_on_error: bool = True
) -> int:
    """
    Run validation and print results.
    
    Returns:
        0 if valid, 1 if invalid (or 2 if warnings in strict mode)
    """
    
    try:
        is_valid, errors, warnings = validate_change_impact(metadata_path, strict)
        
        # Print results
        if errors:
            print("❌ VALIDATION ERRORS:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
        
        if warnings:
            print("⚠️  VALIDATION WARNINGS:")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")
        
        if not errors and not warnings:
            print("✅ Validation passed - change impact is valid and complete")
            return 0
        
        if is_valid and warnings and not strict:
            print(f"\n✅ Validation passed ({len(warnings)} warnings)")
            return 0
        
        if not is_valid:
            print(f"\n❌ Validation failed")
            if exit_on_error:
                sys.exit(1)
            return 1
        
        return 0
    
    except Exception as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        if exit_on_error:
            sys.exit(1)
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate change impact metadata")
    parser.add_argument(
        "--metadata",
        default="change-metadata-enhanced.json",
        help="Path to change metadata JSON file"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings, not just errors"
    )
    parser.add_argument(
        "--no-exit",
        action="store_true",
        help="Don't exit with error code, just return status"
    )
    
    args = parser.parse_args()
    
    exit_code = run_validation(
        metadata_path=args.metadata,
        strict=args.strict,
        exit_on_error=not args.no_exit
    )
    sys.exit(exit_code)
