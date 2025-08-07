# Alternative HuggingFace Repository Downloader

A powerful command-line tool to download all files from a HuggingFace repository with progress tracking, integrity verification, and comprehensive status checking.

## Key Features

- **1:1 repository cloning**: Clones the file structure as shown on HuggingFace repo one to one.
- **Intelligent Download Management**: Advanced analysis for partial downloads, data corruption and SHA256 checksum verification
- **Streaming Downloads**: Efficient handling of large files (tested successfully on 60GB+ file sizes). Automatically resumes interrupted downloads

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--check` | `-c` | Check repository status and file integrity without downloading |
| `--force` | `-f` | Force re-download all files even if they already exist |
| `--force-files` | | Force re-download specific files (provide relative paths) |
| `--verbose` | `-v` | Enable verbose output with detailed error information |


## Usage

### Basic Usage

Downloads a repository to the default Hugging Face location as `{default_hf_path}/models/{organization}/{model_name}/`.

| Platform      | Default Hugging Face Path                         |
|---------------|---------------------------------------------------|
| Linux/macOS   | `~/.cache/huggingface/`                           |
| Windows       | `C:\Users\<YourUsername>\.cache\huggingface\`     |


Uses the alternative location if Hugging Face's `HF_HOME` environment variable is set. For example, `mlx-community/Qwen3-Embedding-0.6B-8bit` will be downloaded to:
`{HF_HOME}/models/mlx-community/Qwen3-Embedding-0.6B-8bit/`

### Custom Download Path

Download to a specific directory:

```bash
python3 download_hf_repo.py mlx-community/Qwen3-Embedding-0.6B-8bit /path/to/custom/download/dir
```

### Repository Status Check

Check repository status and file integrity without downloading (recommended to run before and after large repo downloads, or recheck what has been changed when a repo was updated):

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