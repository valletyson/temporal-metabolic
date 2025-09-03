#!/usr/bin/env python3
"""
Worker script with auto-shutdown for processing temporal-metabolic jobs from SQS
Exits after processing jobs or after idle timeout to save costs
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
import time

# AWS clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Environment variables
QUEUE_URL = os.environ.get('QUEUE_URL')
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'temporal-metabolic-inputs')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'temporal-metabolic-outputs')
AUTO_SHUTDOWN = os.environ.get('AUTO_SHUTDOWN', 'true').lower() == 'true'
MAX_IDLE_POLLS = int(os.environ.get('MAX_IDLE_POLLS', '3'))  # Exit after 3 empty polls (60s)
EXIT_AFTER_JOB = os.environ.get('EXIT_AFTER_JOB', 'false').lower() == 'true'

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

def categorize_reaction(rxn):
    """Categorize a reaction based on its EC number and type"""
    # Check for EC number in annotation
    ec_numbers = []
    if rxn.annotation:
        if 'ec-code' in rxn.annotation:
            ec_val = rxn.annotation['ec-code']
            # Handle both list and string formats
            if isinstance(ec_val, list):
                ec_numbers = ec_val
            else:
                ec_numbers = [ec_val]
        elif 'EC' in rxn.annotation:
            ec_val = rxn.annotation['EC']
            if isinstance(ec_val, list):
                ec_numbers = ec_val
            else:
                ec_numbers = [ec_val]
    
    # Simple categorization based on reaction name and EC number
    for ec_number in ec_numbers:
        if ec_number.startswith('1.11.1.6'):
            return 'catalase'
        elif ec_number.startswith('1.11.1'):
            return 'peroxidase'
        elif ec_number.startswith('1.9.3') or ec_number.startswith('1.4.3'):
            return 'alternative_oxidase'
    
    # Name-based categorization
    rxn_name_lower = rxn.name.lower() if rxn.name else ''
    if 'photosystem ii' in rxn_name_lower or 'ps ii' in rxn_name_lower or 'psii' in rxn_name_lower:
        return 'photosystem_ii'
    elif 'catalase' in rxn_name_lower:
        return 'catalase'
    elif 'peroxidase' in rxn_name_lower:
        return 'peroxidase'
    elif 'oxidase' in rxn_name_lower and 'alternative' in rxn_name_lower:
        return 'alternative_oxidase'
    elif 'cytochrome' in rxn_name_lower and 'oxidase' in rxn_name_lower:
        return 'cytochrome_oxidase'
    
    return 'other_oxygen'

def analyze_model_simple(model, era='archean'):
    """Simplified analysis - identify oxygen-related reactions for Archean era"""
    anachronistic_reactions = []
    category_counts = {
        'photosystem_ii': 0,
        'catalase': 0,
        'peroxidase': 0,
        'alternative_oxidase': 0,
        'cytochrome_oxidase': 0,
        'other_oxygen': 0
    }
    
    # For Archean era, oxygen-producing reactions are anachronistic
    if era == 'archean':
        for rxn in model.reactions:
            # Check if reaction produces oxygen
            for metabolite, coefficient in rxn.metabolites.items():
                if 'o2' in metabolite.id.lower() and coefficient > 0:
                    category = categorize_reaction(rxn)
                    category_counts[category] += 1
                    
                    anachronistic_reactions.append({
                        'id': rxn.id,
                        'name': rxn.name,
                        'category': category,
                        'reason': 'Oxygen production not possible in Archean era'
                    })
                    break  # Only count once per reaction
    
    return anachronistic_reactions, category_counts

def process_job(message):
    """Process a single job from SQS"""
    body = json.loads(message['Body'])
    job_id = body['job_id']
    model_s3_key = body['model_key']
    options = body.get('options', {})
    
    print(f"Processing job {job_id}")
    start_time = time.time()
    
    try:
        # Download and decompress model
        model_path = download_and_decompress_model(model_s3_key)
        print(f"Downloaded model to {model_path}")
        
        # Load model
        if model_path.endswith('.json'):
            model = cobra.io.load_json_model(model_path)
        else:
            model = cobra.io.read_sbml_model(model_path)
        
        print(f"Loaded model with {len(model.reactions)} reactions")
        
        # Analyze model (simplified version)
        era = options.get('era', 'archean')
        confidence = options.get('min_confidence', 'medium')
        
        # Run simplified analysis
        anachronistic_reactions, category_counts = analyze_model_simple(model, era)
        
        # Create filtered model (remove anachronistic reactions)
        filtered_model = model.copy()
        reactions_to_remove = [r['id'] for r in anachronistic_reactions[:100]]  # Limit for demo
        filtered_model.remove_reactions(reactions_to_remove)
        
        # Prepare results
        results = {
            'job_id': job_id,
            'status': 'completed',
            'processing_time': time.time() - start_time,
            'stats': {
                'total_reactions': len(model.reactions),
                'removed_reactions': len(anachronistic_reactions),
                'percent_anachronistic': (len(anachronistic_reactions) / len(model.reactions)) * 100 if len(model.reactions) > 0 else 0,
                'confidence_used': confidence,
                'era': era,
                'category_counts': category_counts
            },
            'removed_reactions': anachronistic_reactions[:100]  # First 100
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
        print(f"Filtered model uploaded to {filtered_model_key}")
        print(f"Job completed in {time.time() - start_time:.2f} seconds")
        
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
    """Main worker loop with auto-shutdown"""
    if not QUEUE_URL:
        print("ERROR: QUEUE_URL environment variable not set")
        sys.exit(1)
    
    print(f"Worker started. Polling queue: {QUEUE_URL}")
    print(f"Auto-shutdown: {AUTO_SHUTDOWN}, Max idle polls: {MAX_IDLE_POLLS}, Exit after job: {EXIT_AFTER_JOB}")
    
    idle_polls = 0
    jobs_processed = 0
    
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
            
            if not messages:
                idle_polls += 1
                print(f"No messages in queue (idle poll {idle_polls}/{MAX_IDLE_POLLS})")
                
                # Auto-shutdown if idle for too long
                if AUTO_SHUTDOWN and idle_polls >= MAX_IDLE_POLLS:
                    print(f"No messages for {MAX_IDLE_POLLS * 20} seconds, shutting down to save costs")
                    break
            else:
                # Reset idle counter when we get a message
                idle_polls = 0
                
                for message in messages:
                    success = process_job(message)
                    
                    # Delete message if processed successfully
                    if success:
                        sqs.delete_message(
                            QueueUrl=QUEUE_URL,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                        jobs_processed += 1
                        print(f"Job completed and message deleted (total processed: {jobs_processed})")
                        
                        # Exit after processing if configured (useful for demos)
                        if EXIT_AFTER_JOB:
                            print(f"EXIT_AFTER_JOB is enabled, shutting down after processing job")
                            sys.exit(0)
                    else:
                        print(f"Job failed, message will return to queue")
                    
        except KeyboardInterrupt:
            print("Worker shutting down...")
            break
        except Exception as e:
            print(f"Worker error: {str(e)}")
            traceback.print_exc()
            # Continue running unless it's a critical error
    
    print(f"Worker shutdown complete. Processed {jobs_processed} jobs.")

if __name__ == "__main__":
    main()