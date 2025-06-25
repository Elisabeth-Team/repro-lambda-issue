import pulumi
import pulumi_aws as aws
import zipfile
import os

def create_zip_with_repro_zipfile(zip_filename, paths, preserve_structure=False):
    """
    Alternative implementation using repro-zipfile library for guaranteed determinism.
    Install with: pip install repro-zipfile
    """
    try:
        from repro_zipfile import ReproducibleZipFile
    except ImportError:
        print("repro-zipfile not installed. Install with: pip install repro-zipfile")
        return None
    
    # Sort paths for consistent ordering
    sorted_paths = sorted(paths)
    
    with ReproducibleZipFile(zip_filename, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        all_files_to_add = []
        
        # First pass: collect all files
        for path in sorted_paths:
            if os.path.exists(path):
                if os.path.isfile(path):
                    if preserve_structure:
                        arcname = os.path.normpath(path).replace(os.sep, '/')
                        if os.name == 'nt' and len(arcname) > 1 and arcname[1] == ':':
                            arcname = arcname[2:]
                            if arcname.startswith('/'):
                                arcname = arcname[1:]
                    else:
                        arcname = os.path.basename(path)
                    all_files_to_add.append((path, arcname))
                
                elif os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        dirs.sort(key=str.lower)
                        files.sort(key=str.lower)
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            if preserve_structure:
                                arcname = os.path.normpath(file_path).replace(os.sep, '/')
                                if os.name == 'nt' and len(arcname) > 1 and arcname[1] == ':':
                                    arcname = arcname[2:]
                                    if arcname.startswith('/'):
                                        arcname = arcname[1:]
                            else:
                                arcname = os.path.relpath(file_path, os.path.dirname(path))
                                arcname = os.path.normpath(arcname).replace(os.sep, '/')
                            all_files_to_add.append((file_path, arcname))
        
        # Sort and add files
        all_files_to_add.sort(key=lambda x: x[1].lower())
        
        for file_path, arcname in all_files_to_add:
            zipf.write(file_path, arcname=arcname)
            print(f"Added file: {file_path} -> {arcname}")
    
    return zip_filename

def create_lambda_zip():
    """Create a ZIP file for AWS Lambda deployment"""
    paths_to_archive = [
        "./lambdas/worker",           
        "./configs/config.yml",      
        "./schemas/hi.txt",
        "./schemas/what.txt"
    ]
    
    zip_path = "lambda_deployment.zip"
    create_zip_with_repro_zipfile(zip_path, paths_to_archive)
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
