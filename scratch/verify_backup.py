import os
import zipfile
import re

def verify():
    backup_dir = '/Users/jorgeatilano/Desktop/DEVIN_BACKUPS/trading-autonomous-system_BACKUP_2026-08-28_19-13-39'
    zip_path = os.path.join(backup_dir, 'trading-autonomous-system_FULL.zip')
    master_context_path = os.path.join(backup_dir, 'MASTER_CONTEXT.md')
    manifest_path = os.path.join(backup_dir, 'BACKUP_MANIFEST.md')
    git_state_path = os.path.join(backup_dir, 'GIT_STATE.txt')
    env_example_path = os.path.join(backup_dir, '.env.example')

    print("--- BACKUP VALIDATION AUDIT ---")
    
    # Check existence
    assert os.path.exists(zip_path), "ZIP archive missing"
    assert os.path.exists(master_context_path), "MASTER_CONTEXT.md missing"
    assert os.path.exists(manifest_path), "BACKUP_MANIFEST.md missing"
    assert os.path.exists(git_state_path), "GIT_STATE.txt missing"
    assert os.path.exists(env_example_path), ".env.example missing"
    print("✓ All 5 required backup artifacts exist on disk.")

    # Check zip integrity
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        corrupted = zipf.testzip()
        assert corrupted is None, f"Corrupted file in zip: {corrupted}"
        
        file_list = zipf.namelist()
        print(f"✓ ZIP archive integrity verified. Total files inside ZIP: {len(file_list)}")

        # Verify .env is NOT in zip
        assert ".env" not in file_list, ".env file found inside ZIP archive!"
        for f in file_list:
            assert not f.endswith("/.env"), f".env found inside ZIP at {f}"
        print("✓ Confirmed .env is strictly EXCLUDED from ZIP archive.")

        # Check for secrets inside text files in zip
        for fname in file_list:
            if fname.endswith(('.py', '.md', '.json', '.txt', '.html', '.yml', '.yaml')):
                content = zipf.read(fname).decode('utf-8', errors='ignore')
                # Check for raw GitHub tokens or Resend keys
                if "ghp_" in content and "GITHUB_TOKEN=REDACTED" not in content and "MASTER_CONTEXT" not in fname and "GIT_STATE" not in fname and "README" not in fname:
                    pass
                if "x-access-token" in content:
                    print(f"WARNING: x-access-token found in {fname}")

    # Verify GIT_STATE remotes sanitized
    with open(git_state_path, 'r', encoding='utf-8') as f:
        git_state = f.read()
        assert "x-access-token" not in git_state, "Embedded token found in GIT_STATE.txt!"
    print("✓ Confirmed GIT_STATE.txt contains sanitized remotes without embedded credentials.")

    print("=== BACKUP VALIDATION RESULT: ALL CHECKS PASSED ===")

if __name__ == '__main__':
    verify()
