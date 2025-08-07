#!/usr/bin/env python3
"""
HuggingFace Repository Downloader

A CLI tool to download all files from a HuggingFace repository with progress tracking.

Usage:
    python3 download_hf_repo.py <repo_id> [local_path]
    
Examples:
    python3 download_hf_repo.py mlx-community/Qwen3-Embedding-0.6B-8bit
    python3 download_hf_repo.py mlx-community/Qwen3-Embedding-0.6B-8bit /path/to/custom/download/dir
"""

import os
import sys
import argparse
import requests
import hashlib
from tqdm import tqdm
from pathlib import Path
from huggingface_hub import list_repo_tree


def download_hf_repo(repo_id, base_path=None, force_redownload=False, force_files=None):
    """
    Download all files from a HuggingFace repository with progress tracking.
    
    Args:
        repo_id (str): The repository ID (e.g., "mlx-community/Qwen3-Embedding-0.6B-8bit")
        base_path (str, optional): Base path for downloads. If None, uses HF_HOME environment variable.
        force_redownload (bool): If True, re-download all files even if they already exist.
        force_files (list): List of specific files to force re-download.
    
    Returns:
        str: The local path where files were downloaded
    """
    
    def format_size(size_bytes):
        """Convert bytes to human readable format"""
        if size_bytes is None:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    # Parse repo_id to get organization and model name
    if '/' not in repo_id:
        raise ValueError("repo_id must be in format 'organization/model-name'")
    
    hf_org, hf_model = repo_id.split('/', 1)
    
    # Set up paths
    if base_path is None:
        base_path = os.environ.get("HF_HOME", ".")
    
    download_path = Path(base_path) / "models" / hf_org / hf_model
    download_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading {repo_id} to: {download_path}")
    
    # Get list of files with sizes using repo_tree
    try:
        repo_tree = list_repo_tree(repo_id, recursive=True)
        # Filter only files (not directories) - use more robust filtering
        file_items = []
        for item in repo_tree:
            # Check if it's a file by looking for size attribute or type
            is_file = False
            if hasattr(item, 'type'):
                is_file = item.type == 'file'
            elif hasattr(item, 'size') and getattr(item, 'size', None) is not None:
                # If it has a size and size is not None, it's likely a file
                is_file = True
            else:
                # Fallback: assume it's a file if path doesn't end with / and doesn't look like a directory
                path_str = str(item.path)
                is_file = not path_str.endswith('/') and '.' in path_str.split('/')[-1]
            
            if is_file:
                file_items.append(item)
        
        total_size = sum(getattr(item, 'size', 0) or 0 for item in file_items)
        print(f"Found {len(file_items)} files to download ({format_size(total_size)} total)")
        
        # Quick preview of what needs to be downloaded
        missing_files = []
        incomplete_files = []
        for item in file_items:
            local_file_path = download_path / item.path
            expected_size = getattr(item, 'size', None)
            
            if not local_file_path.exists():
                missing_files.append((item.path, expected_size))
            elif expected_size is not None:
                local_size = local_file_path.stat().st_size
                if local_size != expected_size:
                    incomplete_files.append((item.path, local_size, expected_size))
        
        files_to_download = len(missing_files) + len(incomplete_files)
        if files_to_download == 0:
            print("✅ All files already exist with correct sizes!")
            if not force_redownload and not force_files:
                return str(download_path)
        else:
            # Calculate remaining download size (accounting for partial files)
            missing_size = sum(f[1] or 0 for f in missing_files)
            remaining_size = sum((f[2] or 0) - f[1] for f in incomplete_files)
            download_size = missing_size + remaining_size
            
            print(f"📥 Need to download: {files_to_download} files ({format_size(download_size)} remaining)")
            
            if missing_files:
                print(f"  🔴 New/missing: {len(missing_files)} files ({format_size(missing_size)})")
            if incomplete_files:
                print(f"  🟡 Resume/incomplete: {len(incomplete_files)} files ({format_size(remaining_size)} remaining)")
        
    except Exception as e:
        print(f"Error listing files: {e}")
        return None
    
    # Base URL for HuggingFace file downloads
    base_url = f"https://huggingface.co/{repo_id}/resolve/main"
    
    # Download each file with progress tracking
    failed_downloads = []
    successful_downloads = 0
    
    # Process files with simple counter
    for i, item in enumerate(file_items, 1):
        file_path = item.path
        file_size = getattr(item, 'size', None)
        
        try:
            # Create local file path
            local_file_path = download_path / file_path
            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists and is complete
            force_this_file = force_redownload or (force_files and file_path in force_files)
            if local_file_path.exists() and not force_this_file:
                # Verify file integrity
                local_size = local_file_path.stat().st_size
                expected_size = file_size
                
                # If we have expected size info, check if sizes match
                if expected_size is not None:
                    if local_size == expected_size:
                        print(f"Downloading files {i}/{len(file_items)}: Skipping {file_path} (already complete)")
                        successful_downloads += 1
                        continue
                    elif local_size < expected_size:
                        # File exists but is incomplete - try to resume
                        print(f"Downloading files {i}/{len(file_items)}: Resuming {file_path} (from {format_size(local_size)}/{format_size(expected_size)})")
                        # Don't remove the file - we'll resume from this point
                    else:
                        # Local file is larger than expected - corruption, restart
                        print(f"Downloading files {i}/{len(file_items)}: Re-downloading {file_path} (corrupted: {local_size} > {expected_size})")
                        local_file_path.unlink()
                else:
                    # No size info available, try to verify by making a HEAD request
                    try:
                        file_url = f"{base_url}/{file_path}"
                        head_response = requests.head(file_url)
                        if head_response.status_code == 200:
                            remote_size = head_response.headers.get('content-length')
                            if remote_size and int(remote_size) == local_size:
                                print(f"Downloading files {i}/{len(file_items)}: Skipping {file_path} (verified by HEAD request)")
                                successful_downloads += 1
                                continue
                            else:
                                print(f"Downloading files {i}/{len(file_items)}: Re-downloading {file_path} (HEAD verification failed)")
                                local_file_path.unlink()
                        else:
                            # HEAD request failed, assume file is incomplete
                            print(f"Downloading files {i}/{len(file_items)}: Re-downloading {file_path} (HEAD request failed)")
                            local_file_path.unlink()
                    except Exception:
                        # If HEAD request fails, assume file is incomplete
                        print(f"Downloading files {i}/{len(file_items)}: Re-downloading {file_path} (verification failed)")
                        local_file_path.unlink()
            
            # Download file
            file_url = f"{base_url}/{file_path}"
            
            # Check if we need to resume or start fresh
            resume_from = 0
            file_mode = 'wb'
            if local_file_path.exists():
                resume_from = local_file_path.stat().st_size
                file_mode = 'ab'  # Append mode for resuming
            
            # Set up headers for resuming if needed
            headers = {}
            if resume_from > 0:
                headers['Range'] = f'bytes={resume_from}-'
            
            with requests.get(file_url, stream=True, headers=headers) as response:
                response.raise_for_status()
                
                # Check if server supports range requests
                if resume_from > 0 and response.status_code != 206:
                    # Server doesn't support ranges, restart download
                    print(f"Downloading files {i}/{len(file_items)}: Server doesn't support resume, restarting {file_path}")
                    local_file_path.unlink()
                    resume_from = 0
                    file_mode = 'wb'
                    # Retry without range header
                    response.close()
                    response = requests.get(file_url, stream=True)
                    response.raise_for_status()
                
                # Calculate remaining bytes to download
                remaining_bytes = file_size - resume_from if file_size else None
                
                # Show download progress
                if resume_from > 0:
                    print(f"Downloading files {i}/{len(file_items)}: Resuming {file_path} from {format_size(resume_from)} ({format_size(remaining_bytes)} remaining)")
                else:
                    print(f"Downloading files {i}/{len(file_items)}: Downloading {file_path} ({format_size(file_size)})")
                
                with open(local_file_path, file_mode) as f:
                    if file_size and file_size > 0:
                        # For large files, show individual progress
                        if file_size > 10 * 1024 * 1024:  # Files larger than 10MB
                            with tqdm(
                                total=file_size,  # Always show total file size
                                unit='B',
                                unit_scale=True,
                                desc=f"  {file_path}",
                                leave=False,
                                initial=resume_from  # Start progress bar from current position
                            ) as file_pbar:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        file_pbar.update(len(chunk))
                        else:
                            # For smaller files, download without individual progress
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                    else:
                        # No size info, download without progress
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                
                successful_downloads += 1
                
        except Exception as e:
            print(f"Downloading files {i}/{len(file_items)}: Failed: {file_path} - {e}")
            failed_downloads.append(file_path)
            # Clean up partial file
            if local_file_path.exists():
                local_file_path.unlink()
    
    # Summary
    print(f"\nDownload completed!")
    print(f"Successfully downloaded: {successful_downloads}/{len(file_items)} files")
    
    if failed_downloads:
        print(f"Failed downloads: {len(failed_downloads)}")
        for failed_file in failed_downloads:
            print(f"  - {failed_file}")
    
    print(f"Files saved to: {download_path}")
    return str(download_path)


def check_repository_status(repo_id, base_path=None):
    """
    Check repository status and file integrity without downloading.
    
    Args:
        repo_id (str): The repository ID (e.g., "mlx-community/Qwen3-Embedding-0.6B-8bit")
        base_path (str, optional): Base path for downloads. If None, uses HF_HOME environment variable.
    """
    
    def format_size(size_bytes):
        """Convert bytes to human readable format"""
        if size_bytes is None:
            return "N/A"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def check_file_integrity(file_path, repo_id, file_relative_path, sample_size=1024*1024):
        """
        Check file integrity using both checksum verification and zero byte analysis.
        Returns (integrity_status, details_str, suspicious)
        """
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return "Empty", "0 bytes", True
            
            # First try to get checksum from HuggingFace
            try:
                # Get LFS metadata from HuggingFace raw URL
                raw_url = f"https://huggingface.co/{repo_id}/raw/main/{file_relative_path}"
                response = requests.get(raw_url, timeout=10)
                
                if response.status_code == 200 and "oid sha256:" in response.text:
                    # Parse LFS metadata
                    lines = response.text.strip().split('\n')
                    expected_sha256 = None
                    expected_size = None
                    
                    for line in lines:
                        if line.startswith("oid sha256:"):
                            expected_sha256 = line.split(":", 1)[1]
                        elif line.startswith("size "):
                            expected_size = int(line.split(" ", 1)[1])
                    
                    if expected_sha256 and expected_size:
                        # Verify size first (quick check)
                        if file_size != expected_size:
                            return "Size Mismatch", f"{file_size} vs {expected_size} bytes", True
                        
                        # Calculate SHA256 of local file
                        sha256_hash = hashlib.sha256()
                        
                        with open(file_path, 'rb') as f:
                            with tqdm(
                                total=file_size,
                                unit='B',
                                unit_scale=True,
                                desc="    Computing SHA256",
                                leave=False,
                                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                            ) as hash_pbar:
                                for chunk in iter(lambda: f.read(65536), b""):  # 64KB chunks for better performance
                                    if chunk:
                                        sha256_hash.update(chunk)
                                        hash_pbar.update(len(chunk))
                        
                        local_sha256 = sha256_hash.hexdigest()
                        
                        if local_sha256 == expected_sha256:
                            return "Verified", f"SHA256 ✓", False
                        else:
                            return "Checksum Fail", f"SHA256 mismatch", True
            
            except Exception:
                pass  # Fall back to zero-byte analysis
            
            # Fallback to zero-byte analysis if checksum verification fails
            # Sample from beginning, middle, and end
            samples = []
            sample_positions = [0, file_size//2, max(0, file_size - sample_size)]
            
            with open(file_path, 'rb') as f:
                for pos in sample_positions:
                    f.seek(pos)
                    chunk = f.read(min(sample_size, file_size - pos))
                    if chunk:
                        samples.append(chunk)
                
                # Check for trailing zeros specifically
                trailing_zeros = 0
                f.seek(max(0, file_size - sample_size))
                tail_chunk = f.read()
                for byte in reversed(tail_chunk):
                    if byte == 0:
                        trailing_zeros += 1
                    else:
                        break
            
            # Calculate zero percentage from samples
            total_sampled_bytes = sum(len(sample) for sample in samples)
            zero_bytes = sum(sample.count(0) for sample in samples)
            zero_percentage = (zero_bytes / total_sampled_bytes * 100) if total_sampled_bytes > 0 else 0
            
            # Convert trailing zeros to MB
            trailing_zeros_mb = trailing_zeros / (1024 * 1024)
            
            # Flag as suspicious if:
            # 1. More than 20% zeros (typical binary files have much less)
            # 2. More than 10MB of trailing zeros
            suspicious = zero_percentage > 20 or trailing_zeros_mb > 10
            
            if suspicious:
                return "Suspicious", f"{zero_percentage:.1f}% zeros, {trailing_zeros_mb:.1f}MB trailing", True
            else:
                return "Size OK", f"{zero_percentage:.1f}% zeros", False
            
        except Exception as e:
            return "Error", f"Check failed: {e}", False
    
    # Parse repo_id to get organization and model name
    if '/' not in repo_id:
        raise ValueError("repo_id must be in format 'organization/model-name'")
    
    hf_org, hf_model = repo_id.split('/', 1)
    
    # Set up paths
    if base_path is None:
        base_path = os.environ.get("HF_HOME", ".")
    
    download_path = Path(base_path) / "models" / hf_org / hf_model
    
    print(f"Repository: {repo_id}")
    print(f"Organization: {hf_org}")
    print(f"Model: {hf_model}")
    print(f"Download path: {download_path}")
    print(f"Download path exists: {download_path.exists()}")
    
    # Get list of files with sizes
    try:
        repo_tree = list_repo_tree(repo_id, recursive=True)
        # Filter only files (not directories) - use more robust filtering
        file_items = []
        for item in repo_tree:
            # Check if it's a file by looking for size attribute or type
            is_file = False
            if hasattr(item, 'type'):
                is_file = item.type == 'file'
            elif hasattr(item, 'size') and getattr(item, 'size', None) is not None:
                # If it has a size and size is not None, it's likely a file
                is_file = True
            else:
                # Fallback: assume it's a file if path doesn't end with / and doesn't look like a directory
                path_str = str(item.path)
                is_file = not path_str.endswith('/') and '.' in path_str.split('/')[-1]
            
            if is_file:
                file_items.append(item)
        
        total_size = sum(getattr(item, 'size', 0) or 0 for item in file_items)
        print(f"\nFiles to download ({len(file_items)} total, {format_size(total_size)}):")
        print("-" * 120)
        print(f"{'#':>3} {'Status':<30} {'File':<40} {'Size':>10} {'Integrity':<25}")
        print("-" * 120)
        
        suspicious_files = []
        missing_files = []
        incomplete_files = []
        
        for i, item in enumerate(sorted(file_items, key=lambda x: x.path), 1):
            local_file_path = download_path / item.path
            expected_size = getattr(item, 'size', None)
            
            if local_file_path.exists():
                if local_file_path.is_dir():
                    # Skip directories - they shouldn't be in file_items but just in case
                    continue
                    
                local_size = local_file_path.stat().st_size
                
                # Check file integrity for large files
                integrity_info = ""
                if expected_size is not None:
                    if local_size == expected_size:
                        status = "✓ Complete"
                        # Only check integrity for files larger than 10MB to avoid overhead
                        if expected_size > 10 * 1024 * 1024:
                            integrity_status, details, suspicious = check_file_integrity(local_file_path, repo_id, item.path)
                            if suspicious:
                                integrity_info = f"⚠ {details}"
                                suspicious_files.append((item.path, integrity_status, details))
                                status = f"⚠ {integrity_status}"
                            else:
                                integrity_info = f"✓ {details}"
                    else:
                        status = f"⚠ Incomplete ({local_size}/{expected_size})"
                        incomplete_files.append((item.path, local_size, expected_size))
                else:
                    status = "? Unknown (no size info)"
            else:
                status = "○ Missing"
                missing_files.append((item.path, expected_size))
            
            size_str = format_size(expected_size) if expected_size else "N/A"
            print(f"  {i:2d}. {status:<30} {item.path:<40} {size_str:>10} {integrity_info:<25}")
            
        print("-" * 120)
        print(f"Total size: {format_size(total_size)}")
        
        # Summary section with highlighted issues
        issues_found = len(missing_files) + len(incomplete_files) + len(suspicious_files)
        
        if missing_files:
            print(f"\n🔴 Missing files ({len(missing_files)} files):")
            for file_path, expected_size in missing_files:
                size_str = format_size(expected_size) if expected_size else "N/A"
                print(f"  • {file_path} ({size_str})")
        
        if incomplete_files:
            print(f"\n🟡 Incomplete files ({len(incomplete_files)} files):")
            for file_path, local_size, expected_size in incomplete_files:
                local_str = format_size(local_size)
                expected_str = format_size(expected_size) if expected_size else "N/A"
                percent = (local_size / expected_size * 100) if expected_size else 0
                print(f"  • {file_path}: {local_str}/{expected_str} ({percent:.1f}%)")
        
        if suspicious_files:
            print(f"\n🟠 Suspicious files ({len(suspicious_files)} files):")
            print("These files may be corrupted despite having the correct size:")
            for file_path, integrity_status, details in suspicious_files:
                print(f"  • {file_path}: {integrity_status} - {details}")
        
        if issues_found > 0:
            print(f"\nTo download missing/incomplete files, use:")
            print(f"  python3 download_hf_repo.py {repo_id}")
            
            if suspicious_files:
                print(f"\nTo re-download suspicious files, use:")
                file_list = " ".join(f'"{f[0]}"' for f in suspicious_files)
                print(f"  python3 download_hf_repo.py --force-files {file_list} {repo_id}")
        else:
            print(f"\n✅ All files are complete and verified!")
            
    except Exception as e:
        print(f"Error listing files: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Download all files from a HuggingFace repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s mlx-community/Qwen3-Embedding-0.6B-8bit
  %(prog)s mlx-community/Qwen3-Embedding-0.6B-8bit /path/to/custom/download/dir
  %(prog)s --check mlx-community/Qwen3-Embedding-0.6B-8bit
  %(prog)s --force mlx-community/Qwen3-Embedding-0.6B-8bit  # Re-download all files
  %(prog)s --force-files metal/model.bin special_tokens_map.json openai/gpt-oss-120b  # Re-download specific files
        """
    )
    
    parser.add_argument(
        "repo_id",
        help="HuggingFace repository ID (e.g., 'mlx-community/Qwen3-Embedding-0.6B-8bit')"
    )
    
    parser.add_argument(
        "local_path",
        nargs="?",
        help="Optional local path for downloads. If not provided, uses HF_HOME environment variable or current directory"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download all files even if they already exist"
    )
    
    parser.add_argument(
        "--force-files",
        nargs="+",
        help="Force re-download specific files (provide relative paths from repo root)"
    )
    
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check repository status and file integrity without downloading"
    )
    
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Alias for --check (deprecated, use --check instead)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate repo_id format
    if '/' not in args.repo_id:
        print("Error: repo_id must be in format 'organization/model-name'")
        sys.exit(1)
    
    try:
        if args.check or args.preview:
            if args.preview:
                print("⚠️  Note: --preview is deprecated, use --check instead")
            check_repository_status(args.repo_id, args.local_path)
        else:
            download_path = download_hf_repo(args.repo_id, args.local_path, args.force, args.force_files)
            if download_path:
                print(f"\n✅ Download completed successfully!")
            else:
                print("❌ Download failed!")
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
