#!/bin/bash

# Script to stop all running ECS tasks in the temporal-metabolic cluster
# This helps prevent unnecessary costs from idle workers

CLUSTER_NAME="temporal-metabolic-cluster"
REGION="us-east-1"

echo "Checking for running ECS tasks in cluster: $CLUSTER_NAME"

# List all running tasks
TASKS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --region $REGION --query 'taskArns[]' --output text 2>/dev/null)

if [ -z "$TASKS" ]; then
    echo "No running tasks found in cluster $CLUSTER_NAME"
else
    echo "Found running tasks:"
    echo "$TASKS"
    
    # Stop each task
    for TASK in $TASKS; do
        echo "Stopping task: $TASK"
        aws ecs stop-task --cluster $CLUSTER_NAME --task $TASK --region $REGION
        if [ $? -eq 0 ]; then
            echo "Successfully stopped task: $TASK"
        else
            echo "Failed to stop task: $TASK"
        fi
    done
    
    echo "All tasks stop commands have been sent."
fi

# Also check the queue for messages
echo ""
echo "Checking SQS queue for pending messages..."
QUEUE_URL="https://queue.amazonaws.com/903267486661/temporal-metabolic-jobs"

QUEUE_ATTRS=$(aws sqs get-queue-attributes --queue-url $QUEUE_URL --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible --region $REGION 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "Queue status:"
    echo "$QUEUE_ATTRS" | grep -E "ApproximateNumberOfMessages|ApproximateNumberOfMessagesNotVisible"
else
    echo "Could not retrieve queue attributes (AWS CLI might not be configured)"
fi

echo ""
echo "Done! To prevent future costs:"
echo "1. Use the optimized task definition (512 CPU, 1024 memory)"
echo "2. Deploy the auto-shutdown worker"
echo "3. Consider using FARGATE_SPOT for 70% cost savings"