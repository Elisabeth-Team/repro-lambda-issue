import pulumi
import pulumi_aws as aws
import zipfile
import os
import hashlib
import time
from pathlib import Path

def create_zip_with_multiple_files(zip_filename, paths, preserve_structure=False, deterministic=True):
    """
    Create a ZIP file containing multiple files and directories from different paths.
    Ensures IDENTICAL output across different operating systems, including Windows.
    
    Args:
        zip_filename (str): Name of the output ZIP file
        paths (list): List of file and/or directory paths to include
        preserve_structure (bool): Whether to preserve directory structure in ZIP
        deterministic (bool): Whether to create deterministic/reproducible ZIP files
    """
    # Sort paths for consistent ordering
    sorted_paths = sorted(paths)
    
    # Use specific ZIP compression settings for consistency
    with zipfile.ZipFile(zip_filename, 'w', 
                        compression=zipfile.ZIP_DEFLATED,
                        compresslevel=6,
                        allowZip64=False) as zipf:
        
        all_files_to_add = []
        
        # First pass: collect all files and their info
        for path in sorted_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    # Handle individual files
                    if preserve_structure:
                        # Normalize path separators and remove drive letters (Windows)
                        arcname = os.path.normpath(path).replace(os.sep, '/')
                        if os.name == 'nt' and len(arcname) > 1 and arcname[1] == ':':
                            arcname = arcname[2:]  # Remove C: prefix on Windows
                            if arcname.startswith('/'):
                                arcname = arcname[1:]  # Remove leading slash
                    else:
                        arcname = os.path.basename(path)
                    
                    all_files_to_add.append((path, arcname))
                
                elif os.path.isdir(path):
                    # Handle directories - recursively collect all files
                    for root, dirs, files in os.walk(path):
                        # Sort for consistent ordering (case-insensitive for Windows)
                        dirs.sort(key=str.lower)
                        files.sort(key=str.lower)
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            
                            if preserve_structure:
                                # Normalize and remove Windows drive letters
                                arcname = os.path.normpath(file_path).replace(os.sep, '/')
                                if os.name == 'nt' and len(arcname) > 1 and arcname[1] == ':':
                                    arcname = arcname[2:]  # Remove C: prefix
                                    if arcname.startswith('/'):
                                        arcname = arcname[1:]  # Remove leading slash
                            else:
                                # Create relative path from the original directory
                                arcname = os.path.relpath(file_path, os.path.dirname(path))
                                arcname = os.path.normpath(arcname).replace(os.sep, '/')
                            
                            all_files_to_add.append((file_path, arcname))
            else:
                print(f"Warning: Path not found: {path}")
        
        # Sort files by archive name for consistent ordering (case-insensitive)
        all_files_to_add.sort(key=lambda x: x[1].lower())
        
        # Second pass: add files to ZIP with completely consistent metadata
        for file_path, arcname in all_files_to_add:
            # Read file content in binary mode to avoid line ending issues
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Create ZipInfo with fully normalized metadata
            zinfo = zipfile.ZipInfo(filename=arcname)
            
            # Set fixed timestamp for reproducibility
            if deterministic:
                # Use fixed date (1980-01-01 00:00:00) - earliest ZIP timestamp
                zinfo.date_time = (1980, 1, 1, 0, 0, 0)
            else:
                # Use actual file modification time
                file_stat = os.stat(file_path)
                zinfo.date_time = time.localtime(file_stat.st_mtime)[:6]
            
            # Set consistent file attributes regardless of OS
            if deterministic:
                # Detect if file should be executable (by extension or current permissions)
                executable_extensions = {'.sh', '.py', '.pl', '.rb', '.js', '.exe', '.bat', '.cmd'}
                file_ext = os.path.splitext(file_path)[1].lower()
                
                # Check if file is executable by extension or current permissions
                is_executable = (file_ext in executable_extensions or 
                               (hasattr(os, 'access') and os.access(file_path, os.X_OK)))
                
                if is_executable:
                    # Executable: 755
                    zinfo.external_attr = (0o755 & 0o777) << 16
                else:
                    # Regular file: 644
                    zinfo.external_attr = (0o644 & 0o777) << 16
            else:
                # Use actual file permissions
                file_stat = os.stat(file_path)
                zinfo.external_attr = (file_stat.st_mode & 0o777) << 16
            
            # Set compression method consistently
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            
            # Ensure consistent compression level
            zinfo._compresslevel = 6
            
            # Set the file size for consistency
            zinfo.file_size = len(file_data)
            
            # Write file to ZIP with exact binary content
            zipf.writestr(zinfo, file_data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            print(f"Added file: {file_path} -> {arcname}")
        
        print(f"Created deterministic ZIP: {zip_filename}")
        
        # Optional: Print hash for verification
        if deterministic:
            with open(zip_filename, 'rb') as f:
                zip_hash = hashlib.sha256(f.read()).hexdigest()[:16]
                print(f"ZIP hash (first 16 chars): {zip_hash}")


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
