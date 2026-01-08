# CloudFormation Layer Architecture - Visual Reference

## Project Structure
```
poc-cloudformation/
│
├── README.md
├── LAYER_ARCHITECTURE.md          ← Architecture documentation
├── TESTING_GUIDE.md               ← Testing instructions
├── CHANGE_DETECTION_SETUP.md      ← Original setup guide
│
├── cloudformation/
│   ├── layers/                    ← ✅ NEW: Function-based layers
│   │   ├── vpc-layer.yaml         # VPC + networking (foundation)
│   │   ├── lambda-layer.yaml      # Lambda + Lambda IAM
│   │   ├── s3-layer.yaml          # S3 + S3 IAM
│   │   └── ec2-layer.yaml         # EC2 + EC2 IAM + Security Groups
│   │
│   ├── applications/
│   │   ├── cumulus/
│   │   │   ├── root.yaml          # Orchestrator (references layers)
│   │   │   ├── packaged-dev.yaml  # Packaged for S3
│   │   │   ├── packaged-staging.yaml
│   │   │   ├── dev/
│   │   │   │   └── app.json       # Dev parameters (layer flags)
│   │   │   └── staging/
│   │   │       └── app.json       # Staging parameters (layer flags)
│   │   │
│   │   └── retina/
│   │       ├── app.yaml           # Orchestrator (references layers)
│   │       ├── dev/
│   │       │   └── app.json
│   │       └── staging/
│   │           └── app.json
│   │
│   ├── stacks/                    ← ❌ DEPRECATED: Old domain stacks
│   │   ├── infra.yaml             # Can be removed
│   │   ├── storage.yaml           # Can be removed
│   │   └── security.yaml          # Can be removed
│   │
│   └── modules/                   ← ❌ DEPRECATED: Old generic modules
│       ├── iam-policy.yaml        # Replaced by layer IAM
│       └── iam-role.yaml          # Replaced by layer IAM
│
└── scripts/
    ├── change-detection-config.yaml  # ✅ UPDATED: Layer mappings
    ├── change-detection.py           # Detects changes
    ├── prepare-change-meta.py        # Adds CF conditions
    └── validate-change-impact.py     # Validates metadata
```

## Layer Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Root Template                    │
│                    (cumulus/root.yaml or                         │
│                     retina/app.yaml)                             │
│                                                                   │
│  Conditional Deployment Flags:                                   │
│  • DeployVpcLayer: true/false                                    │
│  • DeployS3Layer: true/false                                     │
│  • DeployLambdaLayer: true/false                                 │
│  • DeployEc2Layer: true/false                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┬─────────────┐
                │               │               │             │
                ▼               ▼               ▼             ▼
    ┌───────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐
    │  VPC LAYER    │  │ LAMBDA LAYER │  │ S3 LAYER │  │EC2 LAYER│
    │               │  │              │  │          │  │         │
    │ vpc-layer.yaml│  │lambda-layer  │  │s3-layer  │  │ec2-layer│
    └───────────────┘  └──────────────┘  └──────────┘  └─────────┘
            │                  │              │             │
            │                  │              │             │
            ▼                  ▼              ▼             ▼
    ┌───────────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐
    │ VPC Resources │  │Lambda Func   │  │S3 Bucket │  │EC2 Inst.│
    │ • VPC         │  │Lambda IAM    │  │S3 IAM    │  │EC2 IAM  │
    │ • Subnets     │  │  • Policy    │  │  • Policy│  │  • Policy│
    │ • IGW         │  │  • Role      │  │  • Role  │  │  • Role │
    │ • NAT GW      │  │              │  │  • Profile│ │  • Profile│
    │ • Routes      │  │              │  │          │  │Security │
    │               │  │              │  │          │  │Groups   │
    └───────────────┘  └──────────────┘  └──────────┘  └─────────┘
```

## Change Detection Flow

```
┌────────────────────────────────────────────────────────────────┐
│ 1. CODE CHANGES                                                 │
│                                                                  │
│    Developer makes changes to:                                  │
│    • Lambda code: lambda-function-a/src/handler.py             │
│    • VPC config: cloudformation/layers/vpc-layer.yaml          │
│    • S3 config: config/s3-config.json                          │
│    • EC2 code: modules/ec2/startup.sh                          │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│ 2. GIT DIFF                                                     │
│                                                                  │
│    git diff main HEAD                                           │
│    → Returns list of changed files                             │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│ 3. PATTERN MATCHING (change-detection.py)                      │
│                                                                  │
│    Match files against patterns in config:                     │
│    • lambda-*/src/** → lambda_layer                            │
│    • cloudformation/layers/vpc-layer.yaml → vpc_layer          │
│    • config/**/s3*.json → s3_layer                             │
│    • modules/ec2/** → ec2_layer                                │
│                                                                  │
│    Output: change-metadata.json                                │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│ 4. DEPLOYMENT CHECKLIST                                        │
│                                                                  │
│    {                                                            │
│      "deployment_checklist": {                                 │
│        "vpc_layer": true,      ← VPC template changed          │
│        "lambda_layer": true,   ← Lambda code changed           │
│        "s3_layer": true,       ← S3 config changed             │
│        "ec2_layer": true,      ← EC2 code changed              │
│        "application": false                                    │
│      }                                                          │
│    }                                                            │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│ 5. ENHANCE METADATA (prepare-change-meta.py)                   │
│                                                                  │
│    Add CloudFormation conditions:                              │
│    {                                                            │
│      "cloudformation_conditions": {                            │
│        "DeployVpcLayer": true,                                 │
│        "DeployLambdaLayer": true,                              │
│        "DeployS3Layer": true,                                  │
│        "DeployEc2Layer": true                                  │
│      }                                                          │
│    }                                                            │
│                                                                  │
│    Output: change-metadata-enhanced.json                       │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│ 6. VALIDATE (validate-change-impact.py)                        │
│                                                                  │
│    ✅ Check: Has affected resources?                           │
│    ✅ Check: Deployment checklist not empty?                   │
│    ✅ Check: Conditions generated?                             │
│    ✅ Check: Critical changes have actions?                    │
│                                                                  │
│    Result: VALID ✓                                             │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────────┐
│ 7. CONDITIONAL DEPLOYMENT                                      │
│                                                                  │
│    CloudFormation deploys only layers with true conditions:   │
│                                                                  │
│    ✅ VpcLayer (DeployVpcLayer = true)                         │
│    ✅ LambdaLayer (DeployLambdaLayer = true)                   │
│    ✅ S3Layer (DeployS3Layer = true)                           │
│    ✅ Ec2Layer (DeployEc2Layer = true)                         │
│                                                                  │
│    ⏭️  Skipped layers remain unchanged                         │
└────────────────────────────────────────────────────────────────┘
```

## Layer Dependencies

```
┌─────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT ORDER                         │
└─────────────────────────────────────────────────────────────────┘

    1. VPC Layer (Foundation)
            │
            │ Exports: VpcId, SubnetIds
            │
            ├──────────────┬────────────────┬
            │              │                │
            ▼              ▼                ▼
    2a. Lambda Layer  2b. S3 Layer    2c. EC2 Layer
    (Independent)     (Independent)    (Depends on VPC)
                                       Uses: VpcId, SubnetId

Legend:
    ──▶  Required dependency
    ═══▶ Optional dependency
```

## Example: Lambda Code Change Flow

```
Developer changes Lambda code
         │
         ▼
lambda-function-a/src/handler.py modified
         │
         ▼
Run: python scripts/change-detection.py
         │
         ▼
Pattern matched: lambda-*/src/** → lambda_layer
         │
         ▼
Deployment checklist:
  vpc_layer: false
  lambda_layer: TRUE ✓
  s3_layer: false
  ec2_layer: false
         │
         ▼
CloudFormation condition:
  DeployLambdaLayer: true
         │
         ▼
Deploy root.yaml with condition
         │
         ▼
ONLY Lambda Layer deployed ✓
  • Lambda function updated
  • Lambda IAM unchanged (no changes)
  • Lambda execution role unchanged (no changes)
         │
         ▼
Other layers SKIPPED (no deployment needed) ✓
```

## Benefits Visualization

```
OLD STRUCTURE (Domain-Based)          NEW STRUCTURE (Layer-Based)
════════════════════════════          ══════════════════════════════

┌─────────────────────┐              ┌─────────────────────┐
│  Security Stack     │              │   Lambda Layer      │
│  (All IAM)          │              │  ┌──────────────┐   │
│  ┌──────────────┐   │              │  │Lambda Func  │   │
│  │Lambda IAM    │   │              │  └──────────────┘   │
│  │S3 IAM        │   │              │  ┌──────────────┐   │
│  │EC2 IAM       │   │              │  │Lambda IAM   │   │
│  └──────────────┘   │              │  └──────────────┘   │
└─────────────────────┘              └─────────────────────┘
         ▲                                     ▲
         │                                     │
         │ Depends on                          │ Self-contained
         │                                     │
┌─────────────────────┐              ┌─────────────────────┐
│  Compute Stack      │              │    S3 Layer         │
│  ┌──────────────┐   │              │  ┌──────────────┐   │
│  │Lambda Func   │───┘              │  │S3 Bucket    │   │
│  │EC2 Instance  │                  │  └──────────────┘   │
│  └──────────────┘                  │  ┌──────────────┐   │
└─────────────────────┘              │  │S3 IAM       │   │
                                     │  └──────────────┘   │
Problem:                             └─────────────────────┘
✗ Lambda change requires              
  updating 2 stacks                  Benefit:
✗ IAM separated from resources       ✓ Lambda change updates
✗ Complex dependencies                 1 layer only
                                     ✓ IAM with resources
                                     ✓ Clear encapsulation
```
