import pulumi
import pulumi_aws as aws
import zipfile
import os
from pathlib import Path

def create_zip_with_multiple_files(zip_filename, paths, preserve_structure=False):
    """
    Create a ZIP file containing multiple files and directories from different paths.
    
    Args:
        zip_filename (str): Name of the output ZIP file
        paths (list): List of file and/or directory paths to include
        preserve_structure (bool): Whether to preserve directory structure in ZIP
    """
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for path in paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    # Handle individual files
                    if preserve_structure:
                        arcname = path
                    else:
                        arcname = os.path.basename(path)
                    
                    zipf.write(path, arcname)
                    print(f"Added file: {path} -> {arcname}")
                
                elif os.path.isdir(path):
                    # Handle directories - recursively add all files
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            
                            if preserve_structure:
                                # Keep full directory structure
                                arcname = file_path
                            else:
                                # Create relative path from the original directory
                                arcname = os.path.relpath(file_path, os.path.dirname(path))
                            
                            zipf.write(file_path, arcname)
                            print(f"Added file: {file_path} -> {arcname}")
                        
                        # Add empty directories if preserving structure
                        if preserve_structure and not files and not dirs:
                            dir_arcname = root + '/'
                            zipf.writestr(dir_arcname, '')
                            print(f"Added empty dir: {dir_arcname}")
            else:
                print(f"Warning: Path not found: {path}")

# Pulumi-specific usage examples:

def create_lambda_zip():
    """Create a ZIP file for AWS Lambda deployment"""
    paths_to_archive = [
        "./lambdas/worker",           
        "./configs/config.yml"      
        "./schemas/hi.txt",
        "./schemas/what.txt"
    ]
    
    zip_path = "lambda_deployment.zip"
    create_zip_with_multiple_files(zip_path, paths_to_archive)
    return zip_path

lambda_zip_path = create_lambda_zip()

# Use in Pulumi Lambda function
lambda_function = aws.lambda_.Function(
    "my-lambda",
    code=pulumi.FileArchive(lambda_zip_path),  # Use the created ZIP
    handler="lambda_function.lambda_handler2",
    runtime="python3.9",
    role="arn:aws:iam::052848974346:role/delete-me-elisabeth", # from elsewhere

)
