import pulumi
import pulumi_aws as aws
import zipfile
import os
def create_ultra_deterministic_zip(zip_filename, paths, preserve_structure=False):
    """
    Ultra-deterministic ZIP creation with maximum control over every byte.
    This manually controls even more aspects of the ZIP format.
    """
    # Sort paths for consistent ordering
    sorted_paths = sorted(paths)
    
    # Collect all files first
    all_files_to_add = []
    
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
    
    # Sort by archive name
    all_files_to_add.sort(key=lambda x: x[1].lower())
    
    # Create ZIP with maximum determinism
    with zipfile.ZipFile(zip_filename, 'w', 
                        compression=zipfile.ZIP_DEFLATED,
                        compresslevel=6,
                        allowZip64=False) as zipf:
        
        for file_path, arcname in all_files_to_add:
            # Read and normalize file content
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Normalize line endings for text files
            text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml', 
                             '.md', '.rst', '.csv', '.sql', '.sh', '.bat', '.ps1', '.conf', '.cfg', '.ini'}
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in text_extensions:
                try:
                    text_content = file_data.decode('utf-8', errors='ignore')
                    normalized_content = text_content.replace('\r\n', '\n').replace('\r', '\n')
                    file_data = normalized_content.encode('utf-8')
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass
            
            # Create ZipInfo with maximum control
            zinfo = zipfile.ZipInfo(filename=arcname)
            
            # Set ALL metadata to fixed values
            zinfo.date_time = (1980, 1, 1, 0, 0, 0)  # Fixed timestamp
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zinfo.file_size = len(file_data)
            zinfo.external_attr = (0o644 & 0o777) << 16  # Fixed permissions
            zinfo.create_system = 0  # MS-DOS
            zinfo.extract_version = 20  # Version 2.0
            zinfo.reserved = 0
            zinfo.flag_bits = 0  # No flags
            zinfo.volume = 0
            zinfo.internal_attr = 0
            zinfo.header_offset = 0
            zinfo.CRC = zipfile.crc32(file_data) & 0xffffffff
            
            # Write with exact control
            zipf.writestr(zinfo, file_data)
            print(f"Added: {file_path} -> {arcname}")

def create_lambda_zip():
    """Create a ZIP file for AWS Lambda deployment"""
    paths_to_archive = [
        "./lambdas/worker",           
        "./configs/config.yml",      
        "./schemas/hi.txt",
        "./schemas/what.txt"
    ]
    
    zip_path = "lambda_deployment.zip"
    create_ultra_deterministic_zip(zip_path, paths_to_archive)
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
