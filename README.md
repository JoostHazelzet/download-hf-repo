# Alternative HuggingFace Repository Downloader

A powerful command-line tool to download all files from a HuggingFace repository with progress tracking, integrity verification, and comprehensive status checking.

## Usage

### Basic Usage

Download a repository to the default Hugging Face location. 

| Platform      | Default Path                                      |
|---------------|---------------------------------------------------|
| Linux/macOS   | `~/.cache/huggingface/`                           |
| Windows       | `C:\Users\<YourUsername>\.cache\huggingface\`     |


Uses alternative location if Hugging Face's `HF_HOME` environment variable is set. 

```bash
python3 download_hf_repo.py mlx-community/Qwen3-Embedding-0.6B-8bit
```

## Custom Download Path

Download to a specific directory:

```bash
python3 download_hf_repo.py mlx-community/Qwen3-Embedding-0.6B-8bit /path/to/custom/download/dir
```

### Repository Status Check

Check repository status and file integrity without downloading (recommended before large downloads):

```bash
python3 download_hf_repo.py --check mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8
```

### Force Re-download Options

Force re-download all files:

```bash
python3 download_hf_repo.py --force mlx-community/Qwen3-Embedding-0.6B-8bit
```

Force re-download specific files only:

```bash
python3 download_hf_repo.py --force-files metal/model.bin config.json mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8
```

### Verbose Output

Get detailed error information and stack traces:

```bash
python3 download_hf_repo.py --verbose mlx-community/Qwen3-Embedding-0.6B-8bit
```

## Key Features

### 🔍 **Advanced Status Checking (`--check`)**
- **SHA256 Verification**: Uses HuggingFace Git LFS metadata for cryptographic verification
- **Progress Indicators**: Shows progress for SHA256 calculation on large files (~2.4GB/s throughput)
- **Color-coded Status**: 
  - 🔴 Missing files
  - 🟡 Incomplete files (with percentage completion)
  - 🟠 Suspicious files (corruption detection)
  - ✅ Verified files (SHA256 checksum passed)
- **Detailed Diagnostics**: Zero-byte analysis and trailing data detection
- **Smart Commands**: Suggests exact commands to fix detected issues

### 📥 **Intelligent Download Management**
- **Resume Capability**: Automatically resumes interrupted downloads using HTTP Range requests
- **Smart Resume Logic**: Continues from exact byte position where download stopped
- **Corruption Detection**: Restarts download if local file is larger than expected (corruption)
- **Server Compatibility**: Falls back to full re-download if server doesn't support range requests
- **Size Verification**: Validates file sizes before and after download
- **Smart Preview**: Shows remaining download size accounting for partial files
- **Streaming Downloads**: Efficient handling of large files (60GB+ models)
- **Progress Tracking**: Dual progress bars for overall and individual file progress

### 🛡️ **File Integrity & Safety**
- **SHA256 Checksums**: Cryptographic verification using HuggingFace metadata
- **Corruption Detection**: Advanced analysis for partial downloads and data corruption
- **Fallback Verification**: Zero-byte analysis when checksums unavailable
- **Clean Recovery**: Automatic cleanup of failed/partial downloads
- **Force Options**: Selective or complete re-download capabilities

### 🚀 **Performance & Reliability**
- **64KB Chunk Processing**: Optimized for both download and verification speed
- **Error Resilience**: Continues downloading other files if one fails
- **Memory Efficient**: Streaming approach for large files
- **Network Resilience**: Handles connection issues gracefully

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--check` | `-c` | Check repository status and file integrity without downloading |
| `--force` | `-f` | Force re-download all files even if they already exist |
| `--force-files` | | Force re-download specific files (provide relative paths) |
| `--verbose` | `-v` | Enable verbose output with detailed error information |

## Environment Variables

- `HF_HOME`: Base directory for downloads (default: current directory)

## File Structure

Files are downloaded to: `{base_path}/models/{organization}/{model_name}/`

For example, `mlx-community/Qwen3-Embedding-0.6B-8bit` will be downloaded to:
`{HF_HOME}/models/mlx-community/Qwen3-Embedding-0.6B-8bit/`

## Example Workflows

### � **Interrupted Downloads & Resume Behavior**
```bash
# If download was interrupted, simply run the same command again
python3 download_hf_repo.py mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8

# The script will automatically:
# 1. Check existing files and their sizes
# 2. Resume incomplete downloads from exact byte position
# 3. Skip files that are already complete
# 4. Show remaining download size (not total size)

# Example output for resumed download:
# 📥 Need to download: 2 files (2.8 GB remaining)
#   🔴 New/missing: 1 files (4.9 GB)
#   🟡 Resume/incomplete: 1 files (2.8 GB remaining)
# Downloading files 8/18: Resuming model-00001-of-00006.safetensors from 2.2 GB (2.8 GB remaining)
```

### �🔍 Optional check after Download (Recommended)
To check if files are complete and checksum matches. For example to find out where the changes are when a repo has been updated:

```bash
# Check repository status
python3 download_hf_repo.py --check mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8
```

Depending on missing//incomplete files reporting restart the download or just the missing files only:

```bash
# Download missing/incomplete files
python3 download_hf_repo.py mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8

# Re-download any suspicious files found during check
python3 download_hf_repo.py --force-files "metal/model.bin" mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8
```

## Status Check Output Example

```
Repository: mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8
Files to download (18 total, 24.9 GB):
------------------------------------------------------------------------------------------------------------------------
  # Status                         File                                           Size Integrity                
------------------------------------------------------------------------------------------------------------------------
   1. ✓ Complete                     .gitattributes                               1.5 KB                          
   2. ✓ Complete                     README.md                                    1.0 KB                          
   8. ✓ Complete                     model-00001-of-00006.safetensors             5.0 GB ✓ SHA256 ✓               
   9. ○ Missing                      model-00002-of-00006.safetensors             4.9 GB                          
  10. ⚠ Incomplete (2.1GB/4.9GB)    model-00003-of-00006.safetensors             4.9 GB                          

🔴 Missing files (1 files):
  • model-00002-of-00006.safetensors (4.9 GB)

🟡 Incomplete files (1 files):
  • model-00003-of-00006.safetensors: 2.1 GB/4.9 GB (42.9%)

To download missing/incomplete files, use:
  python3 download_hf_repo.py mlx-community/Qwen3-30B-A3B-Instruct-2507-6bit-DWQ-lr8e-8
```

## License
This script is provided under MIT license.