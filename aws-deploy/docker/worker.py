#!/usr/bin/env python3
"""
Worker script for processing temporal-metabolic jobs from SQS
"""
import json
import os
import sys
import traceback
import gzip
import zipfile
import bz2
import io
from pathlib import Path
import boto3
import cobra
from temporal import analyze_model, filter_model_for_era

# AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Environment variables
QUEUE_URL = os.environ.get('QUEUE_URL')
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'temporal-metabolic-inputs')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'temporal-metabolic-outputs')

def download_and_decompress_model(s3_key):
    """Download and decompress model from S3"""
    filename = Path(s3_key).name
    local_path = f"/tmp/{filename}"
    
    # Download file
    s3.download_file(INPUT_BUCKET, s3_key, local_path)
    
    # Decompress if needed
    if filename.endswith('.gz'):
        with gzip.open(local_path, 'rb') as gz_file:
            content = gz_file.read()
        # Save decompressed content
        decompressed_path = local_path[:-3]  # Remove .gz extension
        with open(decompressed_path, 'wb') as f:
            f.write(content)
        return decompressed_path
        
    elif filename.endswith('.zip'):
        with zipfile.ZipFile(local_path, 'r') as zip_file:
            # Extract first file
            names = zip_file.namelist()
            if names:
                content = zip_file.read(names[0])
                decompressed_path = f"/tmp/{names[0]}"
                with open(decompressed_path, 'wb') as f:
                    f.write(content)
                return decompressed_path
        
    elif filename.endswith('.bz2'):
        with bz2.open(local_path, 'rb') as bz2_file:
            content = bz2_file.read()
        # Save decompressed content
        decompressed_path = local_path[:-4]  # Remove .bz2 extension
        with open(decompressed_path, 'wb') as f:
            f.write(content)
        return decompressed_path
    
    # Not compressed, return as is
    return local_path

def upload_results(job_id, results):
    """Upload results to S3"""
    results_key = f"results/{job_id}/analysis.json"
    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=results_key,
        Body=json.dumps(results, indent=2),
        ContentType='application/json'
    )
    return results_key

def process_job(message):
    """Process a single job from SQS"""
    body = json.loads(message['Body'])
    job_id = body['job_id']
    model_s3_key = body['model_key']
    options = body.get('options', {})
    
    print(f"Processing job {job_id}")
    
    try:
        # Download and decompress model
        model_path = download_and_decompress_model(model_s3_key)
        
        # Load model
        if model_path.endswith('.json'):
            model = cobra.io.load_json_model(model_path)
        else:
            model = cobra.io.read_sbml_model(model_path)
        
        # Analyze model
        era = options.get('era', 'archean')
        confidence = options.get('min_confidence', 'medium')
        
        # Run analysis
        annotations = analyze_model(model)
        filtered_model, stats = filter_model_for_era(
            model, 
            annotations,
            era_name=era,
            min_confidence=confidence
        )
        
        # Prepare results
        results = {
            'job_id': job_id,
            'status': 'completed',
            'stats': {
                'total_reactions': len(model.reactions),
                'removed_reactions': len(stats['removed_reactions']),
                'percent_anachronistic': (len(stats['removed_reactions']) / len(model.reactions)) * 100,
                'confidence_used': confidence,
                'era': era
            },
            'removed_reactions': stats['removed_reactions'][:100],  # First 100
            'annotations': {
                rxn_id: {
                    'ec_number': ann.ec_number,
                    'confidence': ann.confidence,
                    'era_appropriate': ann.era_appropriate
                }
                for rxn_id, ann in list(annotations.reactions.items())[:50]  # Sample
            }
        }
        
        # Upload results
        results_key = upload_results(job_id, results)
        print(f"Results uploaded to {results_key}")
        
        # Save filtered model
        filtered_model_key = f"results/{job_id}/filtered_model.json"
        cobra.io.save_json_model(filtered_model, f"/tmp/filtered_{job_id}.json")
        s3.upload_file(
            f"/tmp/filtered_{job_id}.json",
            OUTPUT_BUCKET,
            filtered_model_key
        )
        
        return True
        
    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        traceback.print_exc()
        
        # Upload error info
        error_results = {
            'job_id': job_id,
            'status': 'failed',
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        upload_results(job_id, error_results)
        return False

def main():
    """Main worker loop"""
    if not QUEUE_URL:
        print("ERROR: QUEUE_URL environment variable not set")
        sys.exit(1)
    
    print(f"Worker started. Polling queue: {QUEUE_URL}")
    
    while True:
        try:
            # Receive messages from SQS
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # Long polling
                VisibilityTimeout=300  # 5 minutes to process
            )
            
            messages = response.get('Messages', [])
            
            for message in messages:
                success = process_job(message)
                
                # Delete message if processed successfully
                if success:
                    sqs.delete_message(
                        QueueUrl=QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    print(f"Job completed and message deleted")
                else:
                    print(f"Job failed, message will return to queue")
                    
        except KeyboardInterrupt:
            print("Worker shutting down...")
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    main()