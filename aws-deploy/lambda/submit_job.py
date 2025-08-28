import json
import boto3
import uuid
import os
from datetime import datetime

# AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')
ecs = boto3.client('ecs')

# Environment variables
QUEUE_URL = os.environ.get('QUEUE_URL', 'https://queue.amazonaws.com/903267486661/temporal-metabolic-jobs')
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'temporal-metabolic-inputs-903267486661')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'temporal-metabolic-outputs-903267486661')
CLUSTER_NAME = os.environ.get('CLUSTER_NAME', 'temporal-metabolic-cluster')
TASK_DEFINITION = os.environ.get('TASK_DEFINITION', 'temporal-metabolic-worker')
SUBNET_IDS = os.environ.get('SUBNET_IDS', '').split(',')
SECURITY_GROUP = os.environ.get('SECURITY_GROUP', '')

def lambda_handler(event, context):
    """
    Lambda handler for job submission
    Expects POST with:
    - action: 'create_job' | 'get_presigned_url' | 'start_job' | 'get_status'
    """
    
    # Parse request
    if isinstance(event.get('body'), str):
        body = json.loads(event['body'])
    else:
        body = event.get('body', {})
    
    action = body.get('action', 'create_job')
    
    # Enable CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }
    
    try:
        if action == 'create_job':
            # Create new job
            job_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # Get filename and file size from request
            filename = body.get('filename', 'model.sbml')
            file_size = body.get('file_size', 0)
            
            # Validate file size (50 MB limit)
            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB in bytes
            if file_size > MAX_FILE_SIZE:
                return {
                    'statusCode': 413,
                    'headers': headers,
                    'body': json.dumps({
                        'error': f'File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f} MB',
                        'file_size': file_size,
                        'max_size': MAX_FILE_SIZE
                    })
                }
            
            # Generate presigned URLs for upload
            model_key = f"models/{job_id}/{filename}"
            upload_url = s3.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': INPUT_BUCKET,
                    'Key': model_key,
                    'ContentType': 'application/octet-stream'
                },
                ExpiresIn=3600
            )
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'job_id': job_id,
                    'upload_url': upload_url,
                    'model_key': model_key,
                    'created_at': timestamp
                })
            }
        
        elif action == 'start_job':
            # Start processing job
            job_id = body['job_id']
            model_key = body['model_key']
            options = body.get('options', {})
            
            # Send message to SQS
            message = {
                'job_id': job_id,
                'model_key': model_key,
                'options': options
            }
            
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            
            # Start ECS task if we have VPC configuration
            if SUBNET_IDS and SUBNET_IDS[0] and SECURITY_GROUP:
                try:
                    response = ecs.run_task(
                        cluster=CLUSTER_NAME,
                        taskDefinition=TASK_DEFINITION,
                        launchType='FARGATE',
                        networkConfiguration={
                            'awsvpcConfiguration': {
                                'subnets': SUBNET_IDS,
                                'securityGroups': [SECURITY_GROUP],
                                'assignPublicIp': 'ENABLED'
                            }
                        },
                        count=1
                    )
                    task_arn = response['tasks'][0]['taskArn'] if response['tasks'] else None
                except Exception as e:
                    print(f"Failed to start ECS task: {str(e)}")
                    task_arn = None
            else:
                task_arn = None
                print("VPC configuration not set, job queued but ECS task not started")
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': 'Job started',
                    'job_id': job_id,
                    'task_arn': task_arn
                })
            }
        
        elif action == 'get_status':
            # Get job status
            job_id = body['job_id']
            
            # Check for results
            results_key = f"results/{job_id}/analysis.json"
            try:
                # Try to get results
                result = s3.get_object(Bucket=OUTPUT_BUCKET, Key=results_key)
                results = json.loads(result['Body'].read())
                
                # Generate download URLs
                download_urls = {
                    'analysis': s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': OUTPUT_BUCKET, 'Key': results_key},
                        ExpiresIn=3600
                    ),
                    'filtered_model': s3.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': OUTPUT_BUCKET, 'Key': f"results/{job_id}/filtered_model.json"},
                        ExpiresIn=3600
                    )
                }
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'status': results.get('status', 'completed'),
                        'job_id': job_id,
                        'results': results,
                        'download_urls': download_urls
                    })
                }
                
            except s3.exceptions.NoSuchKey:
                # Results not ready yet
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'status': 'processing',
                        'job_id': job_id,
                        'message': 'Job is still processing'
                    })
                }
        
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Unknown action: {action}'})
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }