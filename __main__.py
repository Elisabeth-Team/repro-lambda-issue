import pulumi
import pulumi_aws as aws
import zipfile
import os
import hashlib
import time
from pathlib import Path
import binascii

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
        
def compare_zip_files(zip1_path, zip2_path):
    """
    Compare two ZIP files and show detailed differences.
    Helps debug why ZIP files aren't identical across platforms.
    """
    print(f"\n=== Comparing ZIP files ===")
    print(f"ZIP 1: {zip1_path}")
    print(f"ZIP 2: {zip2_path}")
    
    # Compare file sizes
    size1 = os.path.getsize(zip1_path)
    size2 = os.path.getsize(zip2_path)
    print(f"\nFile sizes: {size1} vs {size2} bytes")
    if size1 != size2:
        print("❌ FILE SIZES DIFFER!")
    
    # Compare file hashes
    with open(zip1_path, 'rb') as f1, open(zip2_path, 'rb') as f2:
        hash1 = hashlib.sha256(f1.read()).hexdigest()
        hash2 = hashlib.sha256(f2.read()).hexdigest()
    
    print(f"\nSHA256 hashes:")
    print(f"ZIP 1: {hash1}")
    print(f"ZIP 2: {hash2}")
    if hash1 == hash2:
        print("✅ Files are identical!")
        return True
    else:
        print("❌ HASHES DIFFER!")
    
    # Compare ZIP contents in detail
    try:
        with zipfile.ZipFile(zip1_path, 'r') as zf1, zipfile.ZipFile(zip2_path, 'r') as zf2:
            info1 = zf1.infolist()
            info2 = zf2.infolist()
            
            print(f"\nNumber of files: {len(info1)} vs {len(info2)}")
            
            # Compare file lists
            files1 = {info.filename for info in info1}
            files2 = {info.filename for info in info2}
            
            if files1 != files2:
                print("❌ FILE LISTS DIFFER!")
                only1 = files1 - files2
                only2 = files2 - files1
                if only1:
                    print(f"  Only in ZIP 1: {only1}")
                if only2:
                    print(f"  Only in ZIP 2: {only2}")
            else:
                print("✅ File lists match")
            
            # Compare each file in detail
            print(f"\n=== File-by-file comparison ===")
            for info1 in sorted(info1, key=lambda x: x.filename):
                filename = info1.filename
                info2 = next((i for i in info2 if i.filename == filename), None)
                
                if not info2:
                    print(f"❌ {filename}: Missing in ZIP 2")
                    continue
                
                print(f"\n📁 {filename}:")
                
                # Compare timestamps
                if info1.date_time != info2.date_time:
                    print(f"  ❌ Timestamps differ: {info1.date_time} vs {info2.date_time}")
                else:
                    print(f"  ✅ Timestamps match: {info1.date_time}")
                
                # Compare file sizes
                if info1.file_size != info2.file_size:
                    print(f"  ❌ File sizes differ: {info1.file_size} vs {info2.file_size}")
                else:
                    print(f"  ✅ File sizes match: {info1.file_size}")
                
                # Compare compressed sizes
                if info1.compress_size != info2.compress_size:
                    print(f"  ❌ Compressed sizes differ: {info1.compress_size} vs {info2.compress_size}")
                else:
                    print(f"  ✅ Compressed sizes match: {info1.compress_size}")
                
                # Compare CRC32
                if info1.CRC != info2.CRC:
                    print(f"  ❌ CRC32 differs: {info1.CRC:08x} vs {info2.CRC:08x}")
                else:
                    print(f"  ✅ CRC32 matches: {info1.CRC:08x}")
                
                # Compare external attributes (permissions)
                if info1.external_attr != info2.external_attr:
                    print(f"  ❌ Permissions differ: {info1.external_attr:08x} vs {info2.external_attr:08x}")
                    print(f"    Octal: {(info1.external_attr >> 16) & 0o777:o} vs {(info2.external_attr >> 16) & 0o777:o}")
                else:
                    print(f"  ✅ Permissions match: {info1.external_attr:08x}")
                
                # Compare compression method
                if info1.compress_type != info2.compress_type:
                    print(f"  ❌ Compression methods differ: {info1.compress_type} vs {info2.compress_type}")
                else:
                    print(f"  ✅ Compression methods match: {info1.compress_type}")
                
                # Compare actual file content
                try:
                    content1 = zf1.read(filename)
                    content2 = zf2.read(filename)
                    
                    if content1 != content2:
                        print(f"  ❌ File contents differ!")
                        print(f"    Content lengths: {len(content1)} vs {len(content2)}")
                        
                        # Show first few bytes if different
                        if len(content1) > 0 and len(content2) > 0:
                            print(f"    First 32 bytes:")
                            print(f"    ZIP 1: {binascii.hexlify(content1[:32])}")
                            print(f"    ZIP 2: {binascii.hexlify(content2[:32])}")
                    else:
                        print(f"  ✅ File contents match")
                        
                except Exception as e:
                    print(f"  ❌ Error reading file contents: {e}")
    
    except Exception as e:
        print(f"❌ Error comparing ZIP files: {e}")
    
    return False

def analyze_zip_structure(zip_path):
    """
    Analyze and display detailed information about a ZIP file's structure.
    """
    print(f"\n=== Analyzing ZIP structure: {zip_path} ===")
    
    # File-level info
    size = os.path.getsize(zip_path)
    with open(zip_path, 'rb') as f:
        content = f.read()
        hash_val = hashlib.sha256(content).hexdigest()
    
    print(f"File size: {size} bytes")
    print(f"SHA256: {hash_val}")
    
    # ZIP structure info
    with zipfile.ZipFile(zip_path, 'r') as zf:
        info_list = zf.infolist()
        print(f"Number of files: {len(info_list)}")
        
        print(f"\n=== File Details ===")
        for info in sorted(info_list, key=lambda x: x.filename):
            print(f"\n📄 {info.filename}")
            print(f"  Date/Time: {info.date_time}")
            print(f"  File size: {info.file_size}")
            print(f"  Compressed size: {info.compress_size}")
            print(f"  CRC32: {info.CRC:08x}")
            print(f"  External attr: {info.external_attr:08x} (perms: {(info.external_attr >> 16) & 0o777:o})")
            print(f"  Compress type: {info.compress_type}")
            print(f"  Header offset: {info.header_offset}")
    
    # Show first 128 bytes of ZIP file in hex
    print(f"\n=== First 128 bytes (hex) ===")
    print(binascii.hexlify(content[:128]).decode('ascii'))
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
