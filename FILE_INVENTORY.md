# File Inventory - Hybrid Layer Architecture

## ✅ Ready for Testing

All files have been refactored to use generic IAM modules + function-based layers.

## Architecture Pattern

**Hybrid Approach:**
- Generic IAM modules (reusable across all layers)
- Function-based layers (Lambda, S3, EC2, VPC)
- Each layer references IAM modules instead of embedding IAM

## Documentation Files

| File | Purpose | Status |
|------|---------|--------|
| `README.md` | Main project overview with hybrid architecture | ✅ Updated |
| `LAYER_ARCHITECTURE.md` | Detailed architecture documentation | ✅ Created |
| `TESTING_GUIDE.md` | Step-by-step testing instructions | ✅ Created |
| `STRUCTURE_DIAGRAM.md` | Visual diagrams and flows | ✅ Created |
| `CHANGE_DETECTION_SETUP.md` | Original setup guide | ✅ Existing |

## CloudFormation Templates

### Generic IAM Modules (Reusable)
| File | Purpose | Status |
|------|---------|--------|
| `cloudformation/modules/iam-policy.yaml` | Generic IAM policies for all layers | ✅ Existing (Active) |
| `cloudformation/modules/iam-role.yaml` | Generic IAM roles module | ✅ Existing (Active) |

### Layers (Function-Based - Reference IAM Modules)
| File | Purpose | Contains | Status |
|------|---------|----------|--------|
| `cloudformation/layers/vpc-layer.yaml` | VPC and networking | VPC, Subnets, IGW, NAT, Routes, NACLs | ✅ Refactored |
| `cloudformation/layers/lambda-layer.yaml` | Lambda compute | Lambda function + IAM module references | ✅ Refactored |
| `cloudformation/layers/s3-layer.yaml` | S3 storage | S3 bucket + IAM module references | ✅ Refactored |
| `cloudformation/layers/ec2-layer.yaml` | EC2 compute | EC2 instance + Security groups + IAM module references | ✅ Refactored |

### Applications
| File | Purpose | Status |
|------|---------|--------|
| `cloudformation/applications/cumulus/root.yaml` | Cumulus orchestrator (references layers) | ✅ Updated |
| `cloudformation/applications/cumulus/dev/app.json` | Cumulus dev parameters | ✅ Updated |
| `cloudformation/applications/cumulus/staging/app.json` | Cumulus staging parameters | ✅ Updated |
| `cloudformation/applications/cumulus/packaged-dev.yaml` | Packaged template | ✅ Existing |
| `cloudformation/applications/cumulus/packaged-staging.yaml` | Packaged template | ✅ Existing |
| `cloudformation/applications/retina/app.yaml` | Retina orchestrator (references layers) | ✅ Updated |
| `cloudformation/applications/retina/dev/app.json` | Retina dev parameters | ✅ Updated |
| `cloudformation/applications/retina/staging/app.json` | Retina staging parameters | ✅ Updated |

### Deprecated (Can be removed)
| File | Status | Action |
|------|--------|--------|
| `cloudformation/stacks/infra.yaml` | ❌ Deprecated | Can remove - replaced by layers |
| `cloudformation/stacks/storage.yaml` | ❌ Deprecated | Can remove - replaced by layers |
| `cloudformation/stacks/security.yaml` | ❌ Deprecated | Can remove - replaced by layers |

## Change Detection Scripts

| File | Purpose | Status |
|------|---------|--------|
| `scripts/change-detection-config.yaml` | Pattern mappings for layer detection | ✅ Updated |
| `scripts/change-detection.py` | Detects changes from git diff | ✅ Existing |
| `scripts/prepare-change-meta.py` | Enhances metadata with CF conditions | ✅ Existing |
| `scripts/validate-change-impact.py` | Validates metadata completeness | ✅ Existing |

## File Count Summary

```
Total Files: 24

Documentation:     5 files  ✅
IAM Modules:       2 files  ✅ ACTIVE (Reusable)
Layer Templates:   4 files  ✅ Refactored (Reference IAM)
App Templates:     2 files  ✅ Updated
App Parameters:    4 files  ✅ Updated
Packaged:          2 files  ✅ Existing
Scripts:           4 files  ✅ (1 updated, 3 existing)
Deprecated:        3 files  ❌ Can be archived (stacks/ only)
```

## What Changed from Original Structure

### Refactored Files
1. ✅ `cloudformation/layers/lambda-layer.yaml` - Now references iam-policy.yaml and iam-role.yaml
2. ✅ `cloudformation/layers/s3-layer.yaml` - Now references iam-policy.yaml and iam-role.yaml
3. ✅ `cloudformation/layers/ec2-layer.yaml` - Now references iam-policy.yaml and iam-role.yaml
4. ✅ `cloudformation/layers/vpc-layer.yaml` - Unchanged (no IAM needed)

### Kept Files (Now Active)
1. ✅ `cloudformation/modules/iam-policy.yaml` - **ACTIVE** - Generic reusable policies
2. ✅ `cloudformation/modules/iam-role.yaml` - **ACTIVE** - Generic reusable roles

### Updated Application Templates
1. ✅ `cloudformation/applications/cumulus/root.yaml` - Updated output names
2. ✅ `cloudformation/applications/retina/app.yaml` - Updated output names

### Deprecated Files (Can Archive)
1. ❌ `cloudformation/stacks/infra.yaml`
2. ❌ `cloudformation/stacks/storage.yaml`
3. ❌ `cloudformation/stacks/security.yaml`

## Testing Checklist

Before running tests, ensure:

- [ ] Python 3.x installed
- [ ] PyYAML installed (`pip install pyyaml`)
- [ ] Git repository initialized with commits
- [ ] AWS CLI installed and configured (for validation/deployment)
- [ ] S3 bucket for CloudFormation artifacts (if deploying)

## Next Steps

1. **Validate Syntax**
   ```bash
   # Test Python scripts
   python -m py_compile scripts/*.py
   
   # Test YAML files
   for f in cloudformation/layers/*.yaml; do
       python -c "import yaml; yaml.safe_load(open('$f'))"
   done
   ```

2. **Test Change Detection**
   ```bash
   # See TESTING_GUIDE.md for detailed scenarios
   python scripts/change-detection.py \
     --config scripts/change-detection-config.yaml \
     --base main --head HEAD \
     --output change-metadata.json
   ```

3. **Validate CloudFormation**
   ```bash
   # Validate each layer
   aws cloudformation validate-template \
     --template-body file://cloudformation/layers/vpc-layer.yaml
   ```

4. **Deploy to Dev**
   ```bash
   # Package and deploy cumulus
   aws cloudformation package \
     --template-file cloudformation/applications/cumulus/root.yaml \
     --s3-bucket your-artifacts-bucket \
     --output-template-file packaged.yaml
   
   aws cloudformation create-stack \
     --stack-name cumulus-dev \
     --template-body file://packaged.yaml \
     --parameters file://cloudformation/applications/cumulus/dev/app.json \
     --capabilities CAPABILITY_NAMED_IAM
   ```

## Architecture Benefits Recap

✅ **Self-Contained**: Each layer has resources + IAM in one file
✅ **Independent**: Change Lambda → deploy Lambda layer only  
✅ **Clear Impact**: Know exactly which layers are affected
✅ **Better Security**: Minimal IAM permissions per layer
✅ **Easy Testing**: Test each layer independently
✅ **Faster Deployments**: Only deploy affected layers
✅ **Clearer Change Detection**: Precise pattern matching

## Support

For questions or issues:
1. Check [LAYER_ARCHITECTURE.md](LAYER_ARCHITECTURE.md) for architecture details
2. Check [TESTING_GUIDE.md](TESTING_GUIDE.md) for testing procedures
3. Check [STRUCTURE_DIAGRAM.md](STRUCTURE_DIAGRAM.md) for visual references
