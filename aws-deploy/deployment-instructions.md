# Cost-Optimized AWS Deployment Instructions

## Immediate Actions to Stop Current Costs

1. **Stop all running ECS tasks immediately:**
```bash
cd aws-deploy
./stop-ecs-tasks.sh
```

Or manually:
```bash
aws ecs list-tasks --cluster temporal-metabolic-cluster --region us-east-1
aws ecs stop-task --cluster temporal-metabolic-cluster --task <TASK_ARN> --region us-east-1
```

## Deploy Cost-Optimized Version

### 1. Update ECS Task Definition
```bash
# Register the optimized task definition (75% cost reduction)
aws ecs register-task-definition \
  --cli-input-json file://infrastructure/task-definition-optimized.json \
  --region us-east-1
```

### 2. Build and Push New Docker Image
```bash
# Build with auto-shutdown worker
cd docker
docker build -t temporal-metabolic:latest .
docker tag temporal-metabolic:latest 903267486661.dkr.ecr.us-east-1.amazonaws.com/temporal-metabolic:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 903267486661.dkr.ecr.us-east-1.amazonaws.com
docker push 903267486661.dkr.ecr.us-east-1.amazonaws.com/temporal-metabolic:latest
```

### 3. Optional: Enable Fargate Spot (70% additional savings)
Create a capacity provider strategy:
```bash
aws ecs put-cluster-capacity-providers \
  --cluster temporal-metabolic-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE_SPOT,weight=1 \
  --region us-east-1
```

## Cost Comparison

### Previous Configuration
- **CPU:** 2048 units (2 vCPU)
- **Memory:** 8192 MB (8 GB)
- **Cost:** ~$0.072/hour ($51.84/month if running 24/7)
- **Behavior:** Runs indefinitely

### Optimized Configuration
- **CPU:** 512 units (0.5 vCPU)
- **Memory:** 1024 MB (1 GB)
- **Cost:** ~$0.018/hour ($12.96/month if running 24/7)
- **Behavior:** Auto-shuts down after 60 seconds idle
- **With Spot:** ~$0.0054/hour ($3.89/month)

## How the Auto-Shutdown Works

The new worker (`worker_auto_shutdown.py`) includes:

1. **Idle Detection:** Exits after 3 consecutive empty polls (60 seconds)
2. **Environment Variables:**
   - `AUTO_SHUTDOWN=true`: Enable auto-shutdown
   - `MAX_IDLE_POLLS=3`: Number of empty polls before shutdown
   - `EXIT_AFTER_JOB=true`: Exit immediately after processing one job (for demos)

3. **Demo Mode:** For the website examples, set `EXIT_AFTER_JOB=true` to process one job and immediately exit

## Monitoring Costs

Check your costs:
```bash
# View running tasks
aws ecs list-tasks --cluster temporal-metabolic-cluster --region us-east-1

# Check CloudWatch logs for worker activity
aws logs tail /ecs/temporal-metabolic --follow --region us-east-1

# View cost breakdown in AWS Console
# Go to: Billing & Cost Management > Cost Explorer
```

## Additional Cost Savings

1. **Use Lambda Instead:** For jobs < 15 minutes, Lambda is cheaper
2. **Schedule Workers:** Only run during business hours
3. **Use Reserved Instances:** For predictable workloads
4. **Set Billing Alerts:** Get notified when costs exceed threshold

## Why You Had $15 in 2 Days

- Multiple ECS tasks running continuously at 2 vCPU + 8GB RAM
- No auto-termination = tasks keep running even when idle
- ~$0.072/hour × 24 hours × 2 days × multiple tasks = $15+

The optimized configuration reduces this by **75-95%** depending on usage patterns.