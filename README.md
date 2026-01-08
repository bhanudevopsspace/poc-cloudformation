# CloudFormation POC - Hybrid Layer Architecture

## Overview

This CloudFormation POC demonstrates a **hybrid layer architecture** combining:
- **Generic IAM Modules** (reusable across all layers)
- **Function-Based Layers** (resources grouped by function: Lambda, S3, EC2, VPC)

Each layer references the generic IAM modules, eliminating code duplication while maintaining clear functional separation.

## Key Features

- ✅ **Generic IAM Management**: One set of IAM policies/roles serves all layers
- ✅ **Function-Based Layers**: Resources grouped by function (Lambda, S3, EC2, VPC)
- ✅ **Independent Deployment**: Change Lambda code → only deploy Lambda layer
- ✅ **Automated Change Detection**: Git diff → precise layer identification → conditional deployment
- ✅ **Less Code Duplication**: IAM defined once, referenced everywhere
- ✅ **Clear Separation**: IAM is cross-cutting, resources are functional
- ✅ **Easy Testing**: Test and validate each layer independently

## Architecture

### Generic IAM Modules (Reusable)
```
cloudformation/modules/
├── iam-policy.yaml     # Generic policies for all resource types
└── iam-role.yaml       # Generic role module accepting policy ARNs
```

### Function-Based Layers
```
cloudformation/layers/
├── vpc-layer.yaml      # VPC + networking (no IAM needed)
├── lambda-layer.yaml   # Lambda + references iam-policy/iam-role
├── s3-layer.yaml       # S3 bucket + references iam-policy/iam-role
└── ec2-layer.yaml      # EC2 + Security Groups + references iam-policy/iam-role
```

### Applications
```
cloudformation/applications/
├── cumulus/
│   ├── root.yaml          # Orchestrates layers with conditional deployment
│   ├── dev/app.json       # Dev environment parameters (layer flags)
│   └── staging/app.json   # Staging environment parameters
└── retina/
    ├── app.yaml           # Orchestrates layers with conditional deployment
    ├── dev/app.json
    └── staging/app.json
```

## Quick Start

### 1. Test Change Detection
```bash
# Install dependencies
pip install pyyaml

# Make a change to Lambda code
echo "# Updated" >> lambda-function-a/src/handler.py

# Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base main \
  --head HEAD \
  --output change-metadata.json

# View results - only lambda_layer should be true
cat change-metadata.json | grep deployment_checklist -A 6
```

### 2. Validate Templates
```bash
# Validate all layer templates
aws cloudformation validate-template --template-body file://cloudformation/layers/vpc-layer.yaml
aws cloudformation validate-template --template-body file://cloudformation/layers/lambda-layer.yaml
aws cloudformation validate-template --template-body file://cloudformation/layers/s3-layer.yaml
aws cloudformation validate-template --template-body file://cloudformation/layers/ec2-layer.yaml

# Validate application root templates
aws cloudformation validate-template --template-body file://cloudformation/applications/cumulus/root.yaml
```

### 3. Deploy Application
```bash
# Package nested stacks
aws cloudformation package \
  --template-file cloudformation/applications/cumulus/root.yaml \
  --s3-bucket your-cf-artifacts-bucket \
  --output-template-file cloudformation/applications/cumulus/packaged-root.yaml

# Deploy with parameters
aws cloudformation create-stack \
  --stack-name cumulus-dev \
  --template-body file://cloudformation/applications/cumulus/packaged-root.yaml \
  --parameters file://cloudformation/applications/cumulus/dev/app.json \
  --capabilities CAPABILITY_NAMED_IAM
```

## Documentation

- **[LAYER_ARCHITECTURE.md](LAYER_ARCHITECTURE.md)** - Detailed architecture explanation and layer descriptions
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Step-by-step testing instructions with examples
- **[STRUCTURE_DIAGRAM.md](STRUCTURE_DIAGRAM.md)** - Visual diagrams and flow charts
- **[CHANGE_DETECTION_SETUP.md](CHANGE_DETECTION_SETUP.md)** - Original change detection setup guide

## Change Detection Mapping

| File Change | Target Layer | Impact | Deployment |
|-------------|--------------|--------|------------|
| `lambda-*/src/**/*.py` | lambda_layer | HIGH | Lambda only |
| `cloudformation/layers/lambda-layer.yaml` | lambda_layer | HIGH | Lambda only |
| `cloudformation/layers/s3-layer.yaml` | s3_layer | HIGH | S3 only |
| `config/**/s3*.json` | s3_layer | MEDIUM | S3 only |
| `cloudformation/layers/vpc-layer.yaml` | vpc_layer | CRITICAL | VPC only |
| `cloudformation/layers/ec2-layer.yaml` | ec2_layer | HIGH | EC2 only |
| `modules/ec2/**` | ec2_layer | HIGH | EC2 only |
| `lib/**`, `shared/**` | all | CRITICAL | ALL layers |

## Example Scenarios

### Scenario 1: Lambda Code Update
```
Change: lambda-function-a/src/handler.py
Result: Only Lambda layer deploys
Other layers: Unchanged
```

### Scenario 2: S3 Configuration Update
```
Change: config/s3-bucket-config.json
Result: Only S3 layer deploys
Other layers: Unchanged
```

### Scenario 3: Shared Library Update
```
Change: lib/common-utils.py
Result: ALL layers deploy (CRITICAL impact)
Reason: Shared code affects all services
```

## Layer Dependencies

```
VPC Layer (Foundation)
    ↓ (exports VpcId, SubnetIds)
    ├──→ Lambda Layer (Independent)
    ├──→ S3 Layer (Independent)
    └──→ EC2 Layer (Depends on VPC)
```

## Benefits Over Domain-Based Architecture

| Aspect | Domain-Based (Old) | Hybrid Layer (New) |
|--------|-------------------|-------------------|
| **IAM Management** | Scattered across stacks | Centralized generic modules |
| **Code Duplication** | High (IAM repeated) | Low (IAM reused) |
| **Lambda Update** | Update 2+ stacks | Update 1 layer |
| **Change Detection** | Broad impact | Precise layer impact |
| **Testing** | Test multiple stacks | Test single layer |
| **Deployment Time** | Deploy all stacks | Deploy affected layers only |
| **Maintainability** | Complex dependencies | Clear functional separation |

## Layer Structure

Each layer follows this pattern:

```yaml
# Example: Lambda Layer
Resources:
  IAMPolicy:              # ← References generic module
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ../modules/iam-policy.yaml
  
  IAMRole:                # ← References generic module
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: ../modules/iam-role.yaml
      Parameters:
        ReadOnlyPolicyArn: !GetAtt IAMPolicy.Outputs.ReadOnlyPolicyArn
  
  LambdaFunction:         # ← Actual resource
    Type: AWS::Lambda::Function
    Properties:
      Role: !GetAtt IAMRole.Outputs.RoleArn
```

## Project Structure
```
poc-cloudformation/
├── README.md                          # This file
├── LAYER_ARCHITECTURE.md              # Architecture details
├── TESTING_GUIDE.md                   # Testing instructions
├── STRUCTURE_DIAGRAM.md               # Visual diagrams
├── CHANGE_DETECTION_SETUP.md          # Original setup guide
│
├── cloudformation/
│   ├── modules/                       # ✅ Generic IAM (reusable)
│   │   ├── iam-policy.yaml            # Generic policies
│   │   └── iam-role.yaml              # Generic roles
│   │
│   ├── layers/                        # ✅ Function-based layers
│   │   ├── vpc-layer.yaml             # VPC only
│   │   ├── lambda-layer.yaml          # Lambda + references IAM modules
│   │   ├── s3-layer.yaml              # S3 + references IAM modules
│   │   └── ec2-layer.yaml             # EC2 + SG + references IAM modules
│   │
│   ├── applications/                  # Application orchestrators
│   │   ├── cumulus/
│   │   │   ├── root.yaml              # References layers
│   │   │   ├── dev/app.json
│   │   │   └── staging/app.json
│   │   └── retina/
│   │       ├── app.yaml
│   │       ├── dev/app.json
│   │       └── staging/app.json
│   │
│   └── stacks/                        # ❌ DEPRECATED (can be removed)
│
└── scripts/
    ├── change-detection-config.yaml   # Layer pattern mappings
    ├── change-detection.py            # Detect changes
    ├── prepare-change-meta.py         # Add CF conditions
    └── validate-change-impact.py      # Validate metadata
```

## Contributing

When adding new functionality:

1. Create a new layer file in `cloudformation/layers/`
2. Include resource + IAM policies + IAM roles in the same file
3. Add pattern mappings to `scripts/change-detection-config.yaml`
4. Update application root templates to reference the new layer
5. Add layer deployment flag to parameter files

## Testing

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive testing instructions.

Quick test:
```bash
# Run all tests
python scripts/change-detection.py --config scripts/change-detection-config.yaml --base main --head HEAD --output test.json
python scripts/prepare-change-meta.py --metadata test.json --output test-enhanced.json
python scripts/validate-change-impact.py --metadata test-enhanced.json
```

## License

POC - Internal use only