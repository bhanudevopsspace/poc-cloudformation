# Quick Start Testing Guide

## Prerequisites

```bash
# Install Python dependencies
pip install pyyaml

# Ensure you're in a git repository with commits
git status
```

## Testing Change Detection

### Test 1: Lambda Code Change
```bash
# 1. Create a mock Lambda directory
mkdir -p lambda-function-a/src
echo "def handler(event, context): pass" > lambda-function-a/src/handler.py

# 2. Commit the change
git add lambda-function-a/
git commit -m "Add Lambda function"

# 3. Make a change
echo "# Updated handler" >> lambda-function-a/src/handler.py

# 4. Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base HEAD~1 \
  --head HEAD \
  --output change-metadata.json

# 5. View results
cat change-metadata.json
```

**Expected Output:**
```json
{
  "deployment_checklist": {
    "vpc_layer": false,
    "lambda_layer": true,    ← Only Lambda layer affected
    "s3_layer": false,
    "ec2_layer": false,
    "application": false
  }
}
```

### Test 2: VPC Layer Change
```bash
# 1. Modify VPC layer template
echo "# Updated" >> cloudformation/layers/vpc-layer.yaml

# 2. Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base HEAD~1 \
  --head HEAD \
  --output change-metadata.json

# 3. Check results
cat change-metadata.json | grep -A 10 deployment_checklist
```

**Expected Output:**
```json
{
  "deployment_checklist": {
    "vpc_layer": true,       ← Only VPC layer affected
    "lambda_layer": false,
    "s3_layer": false,
    "ec2_layer": false,
    "application": false
  }
}
```

### Test 3: Shared Library Change (All Layers)
```bash
# 1. Create shared library
mkdir -p lib
echo "def common_util(): pass" > lib/utils.py

# 2. Commit and modify
git add lib/
git commit -m "Add shared library"
echo "# Updated" >> lib/utils.py

# 3. Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base HEAD~1 \
  --head HEAD \
  --output change-metadata.json

# 4. Check results
cat change-metadata.json
```

**Expected Output:**
```json
{
  "deployment_checklist": {
    "vpc_layer": false,
    "lambda_layer": true,    ← ALL affected layers = true
    "s3_layer": false,
    "ec2_layer": true,       ← Because shared lib is CRITICAL
    "application": false
  },
  "impact_level": "CRITICAL"
}
```

## Validating CloudFormation Templates

### Validate Individual Layer
```bash
# Validate VPC layer
aws cloudformation validate-template \
  --template-body file://cloudformation/layers/vpc-layer.yaml

# Validate Lambda layer
aws cloudformation validate-template \
  --template-body file://cloudformation/layers/lambda-layer.yaml

# Validate S3 layer
aws cloudformation validate-template \
  --template-body file://cloudformation/layers/s3-layer.yaml

# Validate EC2 layer
aws cloudformation validate-template \
  --template-body file://cloudformation/layers/ec2-layer.yaml
```

### Validate Root Templates
```bash
# Validate cumulus root
aws cloudformation validate-template \
  --template-body file://cloudformation/applications/cumulus/root.yaml

# Validate retina app
aws cloudformation validate-template \
  --template-body file://cloudformation/applications/retina/app.yaml
```

## Deploying Layers

### Deploy VPC Layer Only (Foundation)
```bash
aws cloudformation create-stack \
  --stack-name cumulus-dev-vpc \
  --template-body file://cloudformation/layers/vpc-layer.yaml \
  --parameters \
    ParameterKey=Env,ParameterValue=dev \
    ParameterKey=VpcCidr,ParameterValue=10.0.0.0/16 \
    ParameterKey=PublicSubnetCidr,ParameterValue=10.0.1.0/24 \
    ParameterKey=PrivateSubnetCidr,ParameterValue=10.0.2.0/24 \
    ParameterKey=EnableNatGateway,ParameterValue=true \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name cumulus-dev-vpc
```

### Deploy S3 Layer
```bash
aws cloudformation create-stack \
  --stack-name cumulus-dev-s3 \
  --template-body file://cloudformation/layers/s3-layer.yaml \
  --parameters \
    ParameterKey=Env,ParameterValue=dev \
    ParameterKey=EnableVersioning,ParameterValue=true \
    ParameterKey=EnableEncryption,ParameterValue=true \
  --capabilities CAPABILITY_NAMED_IAM
```

### Deploy Complete Application (All Layers)
```bash
# Package nested stacks first
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

# Monitor deployment
aws cloudformation describe-stack-events \
  --stack-name cumulus-dev \
  --max-items 20
```

## Testing Change Detection Workflow

### Full Workflow Test
```bash
# 1. Baseline commit
git add .
git commit -m "Baseline commit"

# 2. Make multiple changes
echo "# VPC update" >> cloudformation/layers/vpc-layer.yaml
echo "# Lambda update" >> lambda-function-a/src/handler.py
echo "# Config update" >> config/app-config.json

# 3. Run detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base HEAD~1 \
  --head HEAD \
  --output change-metadata.json

# 4. Enhance metadata with CF conditions
python scripts/prepare-change-meta.py \
  --metadata change-metadata.json \
  --config scripts/change-detection-config.yaml \
  --output change-metadata-enhanced.json

# 5. Validate impact
python scripts/validate-change-impact.py \
  --metadata change-metadata-enhanced.json \
  --strict

# 6. Review what will be deployed
cat change-metadata-enhanced.json | python -m json.tool
```

**Expected Enhanced Output:**
```json
{
  "cloudformation_conditions": {
    "DeployVpcLayer": true,
    "DeployLambdaLayer": true,
    "DeployS3Layer": false,
    "DeployEc2Layer": false,
    "DeployApplicationStack": true
  },
  "has_affected_resources": true,
  "has_deployments": true,
  "is_valid": true
}
```

## Common Testing Scenarios

### Scenario 1: Only Lambda Code Changed
**Files:** `lambda-function-a/src/handler.py`
**Expected:** Only Lambda layer deploys
**Command:**
```bash
python scripts/change-detection.py --config scripts/change-detection-config.yaml --base main --head HEAD --output test1.json
```

### Scenario 2: S3 Configuration Changed
**Files:** `config/s3-config.json`
**Expected:** Only S3 layer deploys
**Command:**
```bash
python scripts/change-detection.py --config scripts/change-detection-config.yaml --base main --head HEAD --output test2.json
```

### Scenario 3: VPC Template Changed
**Files:** `cloudformation/layers/vpc-layer.yaml`
**Expected:** VPC layer deploys (CRITICAL - may trigger dependent layers)
**Command:**
```bash
python scripts/change-detection.py --config scripts/change-detection-config.yaml --base main --head HEAD --output test3.json
```

### Scenario 4: Utility Library Changed
**Files:** `lib/common.py`
**Expected:** ALL layers deploy (CRITICAL impact)
**Command:**
```bash
python scripts/change-detection.py --config scripts/change-detection-config.yaml --base main --head HEAD --output test4.json
```

## Troubleshooting

### Issue: No changes detected
```bash
# Check git status
git status
git diff HEAD~1 HEAD

# Check exclusion patterns
grep -A 20 "exclusions:" scripts/change-detection-config.yaml
```

### Issue: Wrong layer triggered
```bash
# Check pattern matching
python scripts/change-detection.py --config scripts/change-detection-config.yaml --base main --head HEAD --output debug.json
cat debug.json | python -m json.tool | grep -A 5 affected_resources
```

### Issue: Template validation fails
```bash
# Use AWS CLI for detailed errors
aws cloudformation validate-template --template-body file://cloudformation/layers/vpc-layer.yaml

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('cloudformation/layers/vpc-layer.yaml'))"
```

## Next Steps

1. ✅ Run all test scenarios above
2. ✅ Verify change-metadata.json matches expectations
3. ✅ Validate CloudFormation templates
4. ✅ Deploy to dev environment
5. ✅ Test conditional deployment
6. ✅ Integrate with CI/CD pipeline
