# Change Detection System Setup

This is a complete implementation of the change detection system for CloudFormation deployments. It automatically detects file changes, maps them to resources, and generates CloudFormation conditions to deploy only the affected stacks.

## System Overview

```
Changed Files
    ↓
Change Detection (change-detection.py)
    ↓ matches against patterns
change-metadata.json (affected resources + deployment checklist)
    ↓
Prepare Metadata (prepare-change-meta.py)
    ↓ decorates with CF conditions
change-metadata-enhanced.json (includes CloudFormation conditions)
    ↓
Validate Impact (validate-change-impact.py)
    ↓ safety checks
CloudFormation Deployment (app.yaml)
    ↓ uses conditions to conditionally deploy stacks
Only affected child stacks deployed ✓
```

## Files Created

### Configuration
- **`config/change-detection-config.yaml`**: Defines patterns, resource mappings, impact levels, and condition mappings

### Scripts
- **`scripts/pre-ci/change-detection.py`**: Main detection script - analyzes git diffs against patterns
- **`scripts/pre-ci/prepare-change-meta.py`**: Decorates metadata with CloudFormation condition flags
- **`scripts/pre-ci/validate-change-impact.py`**: Validates metadata completeness and consistency

### CloudFormation Modules
- **`cloudformation/modules/iam-policy-readonly.yaml`**: Read-only IAM managed policy (EC2, S3, Lambda, SQS, VPC, CloudFormation, CloudWatch)
- **`cloudformation/modules/iam-role.yaml`**: IAM role that assumes the read-only policy and creates instance profile

### CloudFormation Templates
- **`cloudformation/stacks/app.yaml`**: Master template with conditional nested stacks (VPC, S3, SQS, Lambda, EC2, IAM Policy, IAM Role)
- **`packaged-dev.yaml`**: Packaged template with S3 artifact URLs (for CI/CD pipelines)

### CI/CD
- **`.github/workflows/ci-cd-change-detection.yml`**: GitHub Actions workflow demonstrating the full pipeline

## Configuration Structure

### Pattern Matching (`change-detection-config.yaml`)

Each resource mapping defines:
- **patterns**: Glob patterns to match files (e.g., `lambda-*/src/**`)
- **resource_type**: AWS resource type (AWS::Lambda::Function)
- **impact_level**: CRITICAL, HIGH, MEDIUM, or LOW
- **target_stack**: Which deployment checklist category to trigger (foundation, data, compute, services, observability, application)
- **affected_child_stacks**: Which nested stacks are affected (VPC, Lambda, EC2, etc.)
- **required_actions**: What actions to take (build, package, upload, update, etc.)

### Exclusions

Patterns to ignore:
- Build artifacts (*.gradle, build/, target/)
- IDE files (.idea/, .git/)
- Tests
- CloudFormation templates themselves (avoid re-detecting CF changes as code)

## Usage

### 1. Run Change Detection

Detects changes between two commits and generates metadata:

```bash
python scripts/pre-ci/change-detection.py \
  --config config/change-detection-config.yaml \
  --base main \
  --head HEAD \
  --output change-metadata.json
```

Output example:
```json
{
  "changed_files": ["lambda-function-a/src/main/java/Handler.java"],
  "affected_resources": [
    {
      "file": "lambda-function-a/src/main/java/Handler.java",
      "resource_type": "AWS::Lambda::Function",
      "impact_level": "HIGH",
      "target_stack": "compute",
      "required_actions": ["build", "package", "upload", "update"]
    }
  ],
  "deployment_checklist": {
    "foundation": false,
    "data": false,
    "compute": true,
    "services": false,
    "observability": false,
    "application": false
  },
  "required_actions": ["build", "package", "upload", "update"]
}
```

### 2. Prepare Metadata

Enhances metadata with CloudFormation condition flags:

```bash
python scripts/pre-ci/prepare-change-meta.py \
  --metadata change-metadata.json \
  --config config/change-detection-config.yaml \
  --output change-metadata-enhanced.json
```

Output adds:
```json
{
  "cloudformation_conditions": {
    "DeployFoundationStack": false,
    "DeployDataStack": false,
    "DeployComputeStack": true,
    "DeployServicesStack": false,
    "DeployObservabilityStack": false,
    "DeployApplicationStack": false
  },
  "has_affected_resources": true,
  "has_deployments": true,
  "is_valid": true
}
```

### 3. Validate Impact

Safety checks to ensure nothing was missed:

```bash
python scripts/pre-ci/validate-change-impact.py \
  --metadata change-metadata-enhanced.json
```

Checks:
- ✅ Affected resources exist
- ✅ Deployment checklist is not empty when resources are affected
- ✅ Required actions are defined for CRITICAL resources
- ✅ All resources have required fields

### 4. Deploy with CloudFormation

Pass condition flags to CloudFormation:

```bash
aws cloudformation deploy \
  --region us-west-1 \
  --template-file cloudformation/stacks/app.yaml \
  --stack-name app1-prod \
  --parameter-overrides \
    Env=prod \
    VpcCidr=10.0.0.0/16 \
    PublicSubnetCidr=10.0.1.0/24 \
    PrivateSubnetCidr=10.0.2.0/24 \
    KeyName=cft-prod \
    DeployFoundationStack=false \
    DeployDataStack=false \
    DeployComputeStack=true \
    DeployServicesStack=false \
    DeployObservabilityStack=false \
    DeployApplicationStack=false \
  --capabilities CAPABILITY_NAMED_IAM
```

**Result**: Only the Lambda and EC2 nested stacks deploy (compute stack). VPC, S3, SQS remain unchanged.

## CloudFormation Template Changes

The `app.yaml` now has:

### New Parameters
Six deployment flag parameters (all string "true"/"false"):
- `DeployFoundationStack` (default: true)
- `DeployDataStack` (default: true)
- `DeployComputeStack` (default: true)
- `DeployServicesStack` (default: true)
- `DeployObservabilityStack` (default: false)
- `DeployApplicationStack` (default: false)

### Conditions
```yaml
Conditions:
  CreateFoundationStack: !Equals [!Ref DeployFoundationStack, "true"]
  CreateDataStack: !Equals [!Ref DeployDataStack, "true"]
  CreateComputeStack: !Equals [!Ref DeployComputeStack, "true"]
  CreateServicesStack: !Equals [!Ref DeployServicesStack, "true"]
  CreateObservabilityStack: !Equals [!Ref DeployObservabilityStack, "true"]
  CreateApplicationStack: !Equals [!Ref DeployApplicationStack, "true"]
```

### Resource Conditions
Each nested stack now has a `Condition` attribute:
```yaml
Resources:
  VPC:
    Type: AWS::CloudFormation::Stack
    Condition: CreateFoundationStack  # ← Only creates if true
    ...
  Lambda:
    Type: AWS::CloudFormation::Stack
    Condition: CreateComputeStack  # ← Only creates if true
    ...
```

## Adding New Resources

To add a new resource to change detection:

1. **Update `config/change-detection-config.yaml`**:
   ```yaml
   my_new_resource:
     patterns:
       - "path/to/files/**"
     resource_type: "AWS::SomeService::Resource"
     impact_level: "HIGH"
     target_stack: "compute"  # or foundation, data, services, etc.
     affected_child_stacks:
       - "MyStack"
     required_actions:
       - "update"
   ```

2. **Create the module template** (e.g., `cloudformation/modules/mynewmodule.yaml`)

3. **Update `cloudformation/stacks/app.yaml`**:
   ```yaml
   MyNewStack:
     Type: AWS::CloudFormation::Stack
     Condition: CreateComputeStack  # Use existing condition or create new one
     Properties:
       TemplateURL: ../modules/mynewmodule.yaml
       Parameters:
         # Pass parameters as needed
   ```

4. **Update `packaged-dev.yaml`** similarly with S3 artifact URLs:
   ```yaml
   MyNewStack:
     Type: AWS::CloudFormation::Stack
     Condition: CreateComputeStack
     Properties:
       TemplateURL: https://s3.region.amazonaws.com/bucket/mynewmodule.template
   ```

## IAM Modules

The repository includes ready-to-use IAM modules:

### `cloudformation/modules/iam-policy-readonly.yaml`
- Managed policy with read-only permissions for EC2, S3, Lambda, SQS, VPC, CloudFormation, CloudWatch
- **Parameter**: `PolicyName` (default: ReadOnlyPolicy)
- **Exports**: `PolicyArn`, `PolicyName`
- **Change Detection**: Mapped to `foundation` stack; HIGH impact

### `cloudformation/modules/iam-role.yaml`
- IAM role that assumes the read-only policy
- Creates instance profile for EC2
- **Parameters**:
  - `RoleName` (default: ReadOnlyRole)
  - `ReadOnlyPolicyArn` (required, pass from IAMPolicy stack output)
  - `AssumeRoleServicePrincipal` (default: ec2.amazonaws.com, lambda.amazonaws.com)
  - `MaxSessionDuration` (default: 3600 seconds)
- **Exports**: `RoleArn`, `RoleName`, `InstanceProfileArn`, `InstanceProfileName`
- **Change Detection**: Mapped to `foundation` stack; HIGH impact

**Integration Example** (in `app.yaml`):
```yaml
IAMPolicy:
  Type: AWS::CloudFormation::Stack
  Condition: CreateFoundationStack
  Properties:
    TemplateURL: ../modules/iam-policy-readonly.yaml
    Parameters:
      PolicyName: !Sub 'ReadOnlyPolicy-${Env}'

IAMRole:
  Type: AWS::CloudFormation::Stack
  Condition: CreateFoundationStack
  DependsOn: IAMPolicy
  Properties:
    TemplateURL: ../modules/iam-role.yaml
    Parameters:
      RoleName: !Sub 'ReadOnlyRole-${Env}'
      ReadOnlyPolicyArn: !GetAtt IAMPolicy.Outputs.PolicyArn
```

## CI/CD Integration

The `.github/workflows/ci-cd-change-detection.yml` demonstrates:

1. **Change Detection Job**: Runs the three scripts, extracts conditions
2. **Build Job**: Only runs if changes detected, runs tests based on affected resources
3. **Deploy Job**: Runs on main branch, passes condition flags to CloudFormation

Outputs from change detection are available to downstream jobs as:
- `deploy-foundation`
- `deploy-data`
- `deploy-compute`
- `deploy-services`

````

## Common Scenarios

### Scenario 1: Lambda Code Change

**File changed**: `lambda-my-function/src/main/java/Handler.java`

1. Detection matches `lambda-*/src/**` pattern
2. Sets `deployment_checklist.compute = true`
3. Sets `DeployComputeStack = true`
4. CloudFormation creates/updates Lambda and EC2 stacks only
5. VPC, S3, SQS, IAM remain unchanged

### Scenario 2: IAM Policy Change

**File changed**: `cloudformation/modules/iam-policy-readonly.yaml`

1. Detection matches `cloudformation/modules/iam-policy-readonly.yaml` pattern
2. Sets `deployment_checklist.foundation = true`
3. Sets `DeployFoundationStack = true`
4. CloudFormation updates IAMPolicy, IAMRole, and VPC stacks
5. S3, SQS, Lambda, EC2 remain unchanged

### Scenario 3: Utility Library Change

**File changed**: `lib/common-utilities/src/main/java/Utils.java`

1. Detection matches `lib/**` pattern (CRITICAL)
2. Sets `deployment_checklist` for ALL stacks (target_stack: "all")
3. Sets all CloudFormation conditions to `true`
4. CloudFormation deploys all stacks (full deployment)
5. All Lambda and EC2 instances rebuild with new library

### Scenario 4: VPC Configuration Change

**File changed**: `cloudformation/modules/vpc.yaml`

1. Excluded by `cloudformation/**` exclusion pattern
2. No affected resources detected
3. No CloudFormation conditions set to true
4. Deployment skipped (no changes to deploy)

### Scenario 5: Config-Only Change

**File changed**: `config/environments/application1/dev/app.json`

1. Detection matches `config/**/*.json` pattern
2. Sets `deployment_checklist.application = true`
3. Sets `DeployApplicationStack = true`
4. CloudFormation can reload configuration
5. Infrastructure unchanged
5. All Lambda and EC2 instances rebuild with new library

### Scenario 3: VPC Configuration Change

**File changed**: `cloudformation/modules/vpc.yaml`

1. Excluded by `cloudformation/**` exclusion pattern
2. No affected resources detected
3. No CloudFormation conditions set to true
4. Deployment skipped (no changes to deploy)

### Scenario 4: Config-Only Change

**File changed**: `config/environments/application1/prod/app.json`

1. Detection matches `config/**/*.json` pattern
2. Sets `deployment_checklist.application = true`
3. Sets `DeployApplicationStack = true`
4. CloudFormation can reload configuration
5. Infrastructure unchanged

## Troubleshooting

### No affected resources detected

**Cause**: Patterns don't match your file structure

**Solution**:
1. Check file paths: Use `/` not `\` in patterns
2. Verify git is tracking files: `git status`
3. Test patterns: `python -c "import fnmatch; print(fnmatch.fnmatch('lambda-func/src/Main.java', 'lambda-*/src/**'))"`

### CloudFormation conditions not applied

**Cause**: Condition flags not passed to `aws cloudformation deploy`

**Solution**: Ensure all 6 Deploy* parameters are in the parameter-overrides

### Validation fails

**Cause**: Metadata validation errors

**Solution**: Run validation with verbose output:
```bash
python scripts/pre-ci/validate-change-impact.py --metadata change-metadata-enhanced.json --strict
```

## Next Steps

1. Customize `config/change-detection-config.yaml` for your exact project structure
2. Test the scripts locally: `python scripts/pre-ci/change-detection.py --help`
3. Integrate into CI/CD pipeline (GitHub Actions, GitLab CI, Jenkins, etc.)
4. Add module-level conditions to child stacks if needed
5. Consider caching build artifacts based on `required_actions`

## References

- Configuration file: [config/change-detection-config.yaml](../config/change-detection-config.yaml)
- Change detection script: [scripts/pre-ci/change-detection.py](../scripts/pre-ci/change-detection.py)
- Metadata preparation script: [scripts/pre-ci/prepare-change-meta.py](../scripts/pre-ci/prepare-change-meta.py)
- Validation script: [scripts/pre-ci/validate-change-impact.py](../scripts/pre-ci/validate-change-impact.py)
- Updated CloudFormation template: [cloudformation/stacks/app.yaml](../cloudformation/stacks/app.yaml)
- CI/CD workflow: [.github/workflows/ci-cd-change-detection.yml](../.github/workflows/ci-cd-change-detection.yml)
