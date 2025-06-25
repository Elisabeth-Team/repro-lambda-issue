import pulumi
import pulumi_aws as aws
import zipfile
import os
import stat
import time
from pathlib import Path
def create_zip_with_multiple_files(zip_filename, paths, preserve_structure=False, deterministic=True):
    """
    Create a ZIP file containing multiple files and directories from different paths.
    Ensures identical output across different operating systems.
    
    Args:
        zip_filename (str): Name of the output ZIP file
        paths (list): List of file and/or directory paths to include
        preserve_structure (bool): Whether to preserve directory structure in ZIP
        deterministic (bool): Whether to create deterministic/reproducible ZIP files
    """
    # Sort paths for consistent ordering
    sorted_paths = sorted(paths)
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        # Set consistent compression level for reproducibility
        
        all_files_to_add = []
        
        # First pass: collect all files and their info
        for path in sorted_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    # Handle individual files
                    if preserve_structure:
                        arcname = path.replace(os.sep, '/')  # Use forward slashes
                    else:
                        arcname = os.path.basename(path)
                    
                    all_files_to_add.append((path, arcname))
                
                elif os.path.isdir(path):
                    # Handle directories - recursively collect all files
                    for root, dirs, files in os.walk(path):
                        # Sort for consistent ordering
                        dirs.sort()
                        files.sort()
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            
                            if preserve_structure:
                                # Keep full directory structure with forward slashes
                                arcname = file_path.replace(os.sep, '/')
                            else:
                                # Create relative path from the original directory
                                arcname = os.path.relpath(file_path, os.path.dirname(path))
                                arcname = arcname.replace(os.sep, '/')  # Use forward slashes
                            
                            all_files_to_add.append((file_path, arcname))
            else:
                print(f"Warning: Path not found: {path}")
        
        # Sort files by archive name for consistent ordering
        all_files_to_add.sort(key=lambda x: x[1])
        
        # Second pass: add files to ZIP with consistent metadata
        for file_path, arcname in all_files_to_add:
            # Get file stats
            file_stat = os.stat(file_path)
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Create ZipInfo with consistent metadata
            zinfo = zipfile.ZipInfo(filename=arcname)
            
            if deterministic:
                # Set consistent timestamp (Unix epoch) for reproducible builds
                zinfo.date_time = (1980, 1, 1, 0, 0, 0)
            else:
                # Use actual file modification time
                zinfo.date_time = time.localtime(file_stat.st_mtime)[:6]
            
            # Set file permissions consistently
            # Preserve execute permissions but normalize others
            if file_stat.st_mode & stat.S_IEXEC:
                # Executable file: 755 (rwxr-xr-x)
                zinfo.external_attr = 0o755 << 16
            else:
                # Regular file: 644 (rw-r--r--)
                zinfo.external_attr = 0o644 << 16
            
            # Set compression method
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            
            # Write file to ZIP
            zipf.writestr(zinfo, file_data)
            print(f"Added file: {file_path} -> {arcname}")
        
        print(f"Created deterministic ZIP: {zip_filename}")

# Pulumi-specific usage examples:

def create_lambda_zip():
    """Create a ZIP file for AWS Lambda deployment"""
    paths_to_archive = [
        "./lambdas/worker",           
        "./configs/config.yml",      
        "./schemas/hi.txt",
        "./schemas/what.txt"
    ]
    
    zip_path = "lambda_deployment.zip"
    create_zip_with_multiple_files(zip_path, paths_to_archive, deterministic=True)
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
