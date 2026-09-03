import os
import sys
import zipfile
import hashlib
import shutil
import subprocess

def main():
    project_dir = '/Users/jorgeatilano/Desktop/DEVIN/trading-autonomous-system'
    backup_parent = os.path.expanduser('~/Desktop/DEVIN_BACKUPS')
    timestamp = '2026-08-28_19-13-39'
    backup_dir_name = f'trading-autonomous-system_BACKUP_{timestamp}'
    backup_dir = os.path.join(backup_parent, backup_dir_name)

    os.makedirs(backup_dir, exist_ok=True)

    zip_filename = 'trading-autonomous-system_FULL.zip'
    zip_filepath = os.path.join(backup_dir, zip_filename)

    # Exclude patterns
    exclude_dirs = {'.venv', 'venv', 'env', 'node_modules', '__pycache__', '.pytest_cache', '.git'}
    exclude_files = {'.env', '.DS_Store', 'trading-autonomous-system_FULL.zip'}
    exclude_exts = {'.pyc', '.pyo', '.pyd', '.so', '.dylib', '.tar.gz', '.tgz'}

    file_count = 0
    total_uncompressed_bytes = 0

    print(f'Starting archive creation at: {zip_filepath}')

    with zipfile.ZipFile(zip_filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            
            for file in files:
                if file in exclude_files:
                    continue
                if any(file.endswith(ext) for ext in exclude_exts):
                    continue
                
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, project_dir)
                
                zipf.write(abs_path, arcname=rel_path)
                file_count += 1
                total_uncompressed_bytes += os.path.getsize(abs_path)

    # Calculate SHA-256
    hasher = hashlib.sha256()
    with open(zip_filepath, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    zip_sha256 = hasher.hexdigest()
    zip_size_bytes = os.path.getsize(zip_filepath)
    zip_size_mb = round(zip_size_bytes / (1024 * 1024), 2)

    # Copy MASTER_CONTEXT.md, GIT_STATE.txt, .env.example into backup_dir
    for extra_doc in ['MASTER_CONTEXT.md', 'GIT_STATE.txt', '.env.example']:
        src_doc = os.path.join(project_dir, extra_doc)
        if os.path.exists(src_doc):
            shutil.copy2(src_doc, os.path.join(backup_dir, extra_doc))

    # Git HEAD info
    head_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project_dir).decode().strip()
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=project_dir).decode().strip()

    # Generate BACKUP_MANIFEST.md
    manifest_content = f'''# BACKUP MANIFEST — TRADING-AUTONOMOUS-SYSTEM

- **Backup Timestamp**: {timestamp}
- **Original Project Path**: `{project_dir}`
- **Git Branch**: `{branch}`
- **Git HEAD Commit**: `{head_commit}`
- **Archive Filename**: `{zip_filename}`
- **Archive File Path**: `{zip_filepath}`
- **Archive SHA-256 Hash**: `{zip_sha256}`
- **Archive Size**: `{zip_size_mb} MB` ({zip_size_bytes} bytes)
- **Total Archived File Count**: `{file_count}`
- **Total Uncompressed Size**: `{round(total_uncompressed_bytes / (1024*1024), 2)} MB`

---

### Excluded Items (Strict Security Policy):
- `.env` (contains sensitive API keys & secrets)
- PayPal API credentials & webhook secrets
- GitHub OAuth/PAT tokens
- Resend API keys
- `node_modules` & `venv` virtual environments
- Python bytecode (`__pycache__`, `.pyc`, `.pyo`)
- Local OS system caches (`.DS_Store`)

---

### Secret Handling Policy:
All sensitive environment variables are sanitized. A redacted template `.env.example` is included in both the project root and backup bundle. All git remote URLs in `GIT_STATE.txt` have embedded authentication tokens stripped.

---

### Included Master Documents:
1. `trading-autonomous-system_FULL.zip` — Full source archive
2. `MASTER_CONTEXT.md` — Self-contained context guide for future LLM continuation
3. `GIT_STATE.txt` — Git commit history, remotes, status, and diff
4. `.env.example` — Redacted environment template
'''

    manifest_path = os.path.join(backup_dir, 'BACKUP_MANIFEST.md')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)

    # Also copy manifest into project root for reference
    shutil.copy2(manifest_path, os.path.join(project_dir, 'BACKUP_MANIFEST.md'))

    print("SUCCESS")
    print(f"BACKUP_DIRECTORY = {backup_dir}")
    print(f"ARCHIVE = {zip_filepath}")
    print(f"MASTER_CONTEXT = {os.path.join(backup_dir, 'MASTER_CONTEXT.md')}")
    print(f"MANIFEST = {manifest_path}")
    print(f"GIT_HEAD = {head_commit}")
    print(f"ARCHIVE_SHA256 = {zip_sha256}")
    print(f"ARCHIVE_SIZE_MB = {zip_size_mb}")
    print(f"FILE_COUNT = {file_count}")

if __name__ == '__main__':
    main()
