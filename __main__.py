import pulumi
import pulumi_aws as aws
import hashlib
import os


def calculate_file_hash(file_path):
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return None

def calculate_directory_hash(directory_path):
    """Calculate hash of all files in a directory recursively."""
    hasher = hashlib.sha256()
    
    for root, dirs, files in os.walk(directory_path):
        # Sort to ensure consistent ordering
        dirs.sort()
        files.sort()
        
        for file_name in files:
            file_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(file_path, directory_path)
            
            # Include relative path in hash for structure awareness
            hasher.update(relative_path.encode('utf-8'))
            
            # Include file content in hash
            try:
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
            except (FileNotFoundError, PermissionError):
                # Handle files that can't be read
                hasher.update(b'UNREADABLE_FILE')
    
    return hasher.hexdigest()

def create_asset_archive_with_hash(schemas):
    """Create asset archive and calculate its composite hash."""
    
    # Calculate individual hashes
    worker_hash = calculate_directory_hash('./lambdas/worker')
    config_hash = calculate_file_hash('./configs/config.yml')
    
    schema_hashes = {}
    for file_name in schemas:
        schema_path = f'./schemas/{file_name}'
        schema_hashes[file_name] = calculate_file_hash(schema_path)
    
    # Create composite hash
    composite_hasher = hashlib.sha256()
    composite_hasher.update(f"worker:{worker_hash}".encode('utf-8'))
    composite_hasher.update(f"config:{config_hash}".encode('utf-8'))
    
    for file_name in sorted(schemas):  # Sort for consistency
        file_hash = schema_hashes[file_name]
        composite_hasher.update(f"schema:{file_name}:{file_hash}".encode('utf-8'))
    
    composite_hash = composite_hasher.hexdigest()
    
    # Create the asset archive
    asset = pulumi.asset.AssetArchive({
        '.': pulumi.asset.FileArchive('./lambdas/worker'),
        'config.yml': pulumi.asset.FileAsset('./configs/config.yml'),
        **{
            f'schemas/{file_name}': pulumi.asset.FileAsset(f'./schemas/{file_name}')
            for file_name in schemas
        }
    })
    
    return asset, composite_hash, {
        'worker_hash': worker_hash,
        'config_hash': config_hash,
        'schema_hashes': schema_hashes,
        'composite_hash': composite_hash
    }

schemas = ["hi.txt", "what.txt"]

config = pulumi.Config()
env = config.get("project:environment")

asset = create_asset_archive_with_hash(schemas=schemas)

worker = aws.lambda_.Function(
    resource_name='worker',
    args=aws.lambda_.FunctionArgs(
        name='worker',
        runtime='python3.9',
        role="arn:aws:iam::052848974346:role/delete-me-elisabeth", # from elsewhere
        handler='lambda_function.lambda_handler2',
        source_code_hash=asset[1],
        code=asset[0]
    )
)