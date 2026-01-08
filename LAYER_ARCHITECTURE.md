# Function-Based Layer Architecture

## Overview

This CloudFormation project now uses a **function-based layer architecture** where each layer is self-contained with its resources, IAM policies, and IAM roles. This approach provides better encapsulation, clearer change detection, and independent deployment capabilities.

## Architecture Principles

### Old Structure (Domain-Based)
```
❌ Domain Stacks (Replaced)
├── infra.yaml       # VPC, EC2 (multiple resources)
├── storage.yaml     # S3, databases
└── security.yaml    # All IAM policies and roles for everything
```

**Problems:**
- IAM policies/roles separated from resources
- Changes to Lambda code required updating multiple stacks
- Difficult to determine deployment impact
- Tight coupling between domains

### New Structure (Function-Based Layers)
```
✅ Function-Based Layers (Current)
cloudformation/
├── layers/
│   ├── vpc-layer.yaml      # VPC + networking only
│   ├── lambda-layer.yaml   # Lambda + Lambda IAM + Lambda policies
│   ├── s3-layer.yaml       # S3 buckets + S3 IAM + S3 policies
│   └── ec2-layer.yaml      # EC2 + EC2 IAM + EC2 policies + Security Groups
├── applications/
│   ├── cumulus/
│   │   └── root.yaml       # Orchestrates layers with conditions
│   └── retina/
│       └── app.yaml        # Orchestrates layers with conditions
└── modules/                # Legacy - can be archived
    ├── iam-policy.yaml
    └── iam-role.yaml
```

**Benefits:**
- ✅ Self-contained layers (resource + IAM in one place)
- ✅ Independent deployment (change Lambda → only redeploy Lambda layer)
- ✅ Clear change impact (Lambda code change → Lambda layer only)
- ✅ Better security (each layer has minimal IAM permissions)
- ✅ Easier testing (can test Lambda layer independently)

## Layer Descriptions

### 1. VPC Layer (`vpc-layer.yaml`)
**Purpose:** Network foundation for all other resources

**Contains:**
- VPC with CIDR configuration
- Public and private subnets
- Internet Gateway
- NAT Gateway (optional)
- Route tables and associations
- Network ACLs

**Parameters:**
- `Env`: Environment (dev, staging, prod)
- `VpcCidr`: VPC CIDR block (e.g., 10.0.0.0/16)
- `PublicSubnetCidr`: Public subnet CIDR
- `PrivateSubnetCidr`: Private subnet CIDR
- `EnableNatGateway`: true/false

**Outputs:**
- VpcId, PublicSubnetId, PrivateSubnetId, InternetGatewayId, NatGatewayId

**Deploy First:** Yes (other layers depend on VPC)

---

### 2. Lambda Layer (`lambda-layer.yaml`)
**Purpose:** Lambda functions with complete IAM setup

**Contains:**
- Lambda execution policy (CloudWatch Logs, S3, SQS, VPC access)
- Lambda execution role
- Lambda function(s)

**Parameters:**
- `Env`: Environment
- `LambdaCodeBucket`: S3 bucket for Lambda code
- `LambdaCodeKey`: S3 key for deployment package

**Outputs:**
- LambdaExecutionRoleArn, LambdaExecutionPolicyArn, LambdaFunctionArn, LambdaFunctionName

**IAM Permissions:**
- CloudWatch Logs (write)
- S3 (read/write to stack-scoped buckets)
- SQS (send/receive messages)
- VPC networking (create/describe/delete network interfaces)

---

### 3. S3 Layer (`s3-layer.yaml`)
**Purpose:** S3 storage with access control

**Contains:**
- S3 access policy (bucket operations)
- S3 access role (for EC2 and Lambda)
- S3 instance profile (for EC2)
- S3 bucket with encryption and versioning
- Bucket policy (enforce SSL, block public access)

**Parameters:**
- `Env`: Environment
- `EnableVersioning`: true/false
- `EnableEncryption`: true/false

**Outputs:**
- S3AccessRoleArn, S3AccessPolicyArn, S3AccessInstanceProfileArn, DataBucketName, DataBucketArn

**IAM Permissions:**
- S3 operations (Get, Put, Delete, List)
- Bucket location and versioning info

**Security Features:**
- Public access blocked
- Encryption at rest (AES256)
- Versioning enabled
- Lifecycle policies (IA transition, Glacier archival)
- SSL/TLS enforced

---

### 4. EC2 Layer (`ec2-layer.yaml`)
**Purpose:** EC2 compute with complete IAM and networking setup

**Contains:**
- EC2 access policy (CloudWatch, SSM, S3 read)
- EC2 instance role
- EC2 instance profile
- Security group
- EC2 instance(s)

**Parameters:**
- `Env`: Environment
- `VpcId`: VPC ID (from VPC layer)
- `SubnetId`: Subnet ID (from VPC layer)
- `KeyName`: EC2 key pair name
- `InstanceType`: t3.micro, t3.small, etc.
- `LatestAmiId`: Amazon Linux 2 AMI (from SSM Parameter Store)

**Outputs:**
- EC2InstanceRoleArn, EC2AccessPolicyArn, EC2InstanceProfileArn, EC2SecurityGroupId, EC2InstanceId, EC2PrivateIp

**IAM Permissions:**
- CloudWatch metrics and logs
- EC2 describe operations
- SSM Parameter Store access
- S3 read access

**Dependencies:**
- Requires VPC layer deployed first
- Requires KeyName for SSH access

---

## Application Root Templates

### Cumulus Application (`cumulus/root.yaml`)
Orchestrates layers with conditional deployment flags.

**Parameters:**
- `Env`, `VpcCidr`, `PublicSubnetCidr`, `PrivateSubnetCidr`, `KeyName`
- `DeployVpcLayer`, `DeployS3Layer`, `DeployLambdaLayer`, `DeployEc2Layer`

**Layer Dependencies:**
- VPC → EC2 (EC2 needs VPC and subnet)
- All others are independent

### Retina Application (`retina/app.yaml`)
Similar to cumulus but focused on Lambda and S3.

**Parameters:**
- `Env`, `VpcCidr`, `PublicSubnetCidr`, `PrivateSubnetCidr`
- `DeployVpcLayer`, `DeployS3Layer`, `DeployLambdaLayer`

---

## Change Detection Mapping

### Layer-Based Change Detection
Changes are now mapped to specific layers for precise deployment:

| File Pattern | Target Layer | Impact |
|--------------|--------------|--------|
| `cloudformation/layers/vpc-layer.yaml` | vpc_layer | CRITICAL |
| `cloudformation/layers/lambda-layer.yaml` | lambda_layer | HIGH |
| `lambda-*/src/**/*.py` | lambda_layer | HIGH |
| `cloudformation/layers/s3-layer.yaml` | s3_layer | HIGH |
| `config/**/s3*.json` | s3_layer | MEDIUM |
| `cloudformation/layers/ec2-layer.yaml` | ec2_layer | HIGH |
| `modules/ec2/**` | ec2_layer | HIGH |
| `lib/**`, `shared/**` | all | CRITICAL |

### Deployment Checklist
```yaml
deploymentChecklist:
  vpc_layer:      # VPC, subnets, gateways
  lambda_layer:   # Lambda functions + IAM
  s3_layer:       # S3 buckets + IAM
  ec2_layer:      # EC2 instances + IAM + SGs
  application:    # Root templates
```

### CloudFormation Conditions
```yaml
cloudFormationConditionMapping:
  vpc_layer: "DeployVpcLayer"
  lambda_layer: "DeployLambdaLayer"
  s3_layer: "DeployS3Layer"
  ec2_layer: "DeployEc2Layer"
```

---

## Deployment Examples

### Deploy Only VPC and S3
```json
{
  "Env": "dev",
  "VpcCidr": "10.0.0.0/16",
  "PublicSubnetCidr": "10.0.1.0/24",
  "PrivateSubnetCidr": "10.0.2.0/24",
  "DeployVpcLayer": "true",
  "DeployS3Layer": "true",
  "DeployLambdaLayer": "false",
  "DeployEc2Layer": "false"
}
```

### Deploy All Layers (Full Stack)
```json
{
  "Env": "staging",
  "VpcCidr": "10.0.0.0/16",
  "PublicSubnetCidr": "10.0.1.0/24",
  "PrivateSubnetCidr": "10.0.2.0/24",
  "KeyName": "my-key-pair",
  "DeployVpcLayer": "true",
  "DeployS3Layer": "true",
  "DeployLambdaLayer": "true",
  "DeployEc2Layer": "true"
}
```

### Update Lambda Only (After Code Change)
```json
{
  "Env": "prod",
  "DeployVpcLayer": "false",
  "DeployS3Layer": "false",
  "DeployLambdaLayer": "true",
  "DeployEc2Layer": "false"
}
```

---

## Testing the Change Detection

### 1. Test Lambda Code Change
```bash
# Modify lambda code
echo "# Updated" >> lambda-function-a/src/handler.py

# Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base main \
  --head HEAD \
  --output change-metadata.json

# Expected: lambda_layer = true, others = false
```

### 2. Test VPC Configuration Change
```bash
# Modify VPC layer
vim cloudformation/layers/vpc-layer.yaml

# Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base main \
  --head HEAD \
  --output change-metadata.json

# Expected: vpc_layer = true (CRITICAL impact)
```

### 3. Test Shared Library Change
```bash
# Modify shared library
echo "# Updated" >> lib/common-utils.py

# Run change detection
python scripts/change-detection.py \
  --config scripts/change-detection-config.yaml \
  --base main \
  --head HEAD \
  --output change-metadata.json

# Expected: ALL layers = true (CRITICAL impact)
```

---

## Migration from Old Structure

The old domain-based stacks (infra.yaml, storage.yaml, security.yaml) in `cloudformation/stacks/` are now deprecated. They can be safely removed or archived.

**Old modules** in `cloudformation/modules/` (iam-policy.yaml, iam-role.yaml) are also deprecated as IAM is now embedded in each layer.

---

## Benefits Summary

1. **Encapsulation**: Each layer contains everything it needs
2. **Independence**: Layers can be deployed independently
3. **Clarity**: Easy to see what's deployed and what changed
4. **Security**: Minimal IAM permissions per layer
5. **Testing**: Can test/validate each layer separately
6. **Change Detection**: Precise mapping of changes to layers
7. **Scalability**: Easy to add new layers (SQS, RDS, etc.)

---

## Next Steps

1. ✅ Test change detection with actual file changes
2. ✅ Package templates using AWS CLI
3. ✅ Deploy to dev environment
4. ✅ Validate conditional deployment works
5. ✅ Test CI/CD pipeline integration
