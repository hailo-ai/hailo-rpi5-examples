#!/usr/bin/env python3
'''
Installation script for RPI Examples.
This script will:
1. Load RPI-specific configuration.
2. Clone and install Hailo Apps Infra (its own install.py will create/activate the venv).
3. Install any extra requirements inside that venv.
4. Install the RPI Examples package itself.
'''
import sys
import subprocess
import argparse
import yaml
from pathlib import Path

def load_config(path: Path) -> dict:
    if not path.is_file():
        print(f'❌ Config file not found: {path}')
        sys.exit(1)
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def run(cmd, **kwargs):
    print("🔧 Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, **kwargs)

def git_clone_or_update(repo_url: str, target: Path, branch: str):
    if not target.exists():
        print(f'⬇️ Cloning {repo_url} into {target}...')
        run(['git', 'clone', repo_url, str(target)])
    else:
        print(f'🔄 Repository already at {target}, fetching updates...')
        run(['git', '-C', str(target), 'fetch'])
    print(f'🔀 Checking out {branch}...')
    run(['git', '-C', str(target), 'checkout', branch])

def main():
    parser = argparse.ArgumentParser(description='Install RPI Examples and dependencies')
    parser.add_argument('-c', '--config', type=str, default='config/config.yaml',
                        help='Path to the RPI examples config file')
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    # 1) Clone Hailo Apps Infra
    infra_path_cfg = cfg.get('hailo_apps_infra_path', 'auto')
    default_infra_path = Path('hailo_apps_infra')
    infra_branch_cfg = cfg.get('hailo_apps_infra_branch_tag', 'auto')
    infra_branch = infra_branch_cfg if infra_branch_cfg != 'auto' else 'main'

    if str(infra_path_cfg).lower() == 'auto':
        infra_path = default_infra_path
        infra_repo_url = cfg.get(
            'hailo_apps_infra_repo_url',
            'https://github.com/hailo-ai/hailo-apps-infra.git'
        )
        git_clone_or_update(infra_repo_url, infra_path, infra_branch)
    else:
        infra_path = Path(infra_path_cfg)
        if not infra_path.exists():
            print(f'❌ Provided Hailo Apps Infra path does not exist: {infra_path}')
            sys.exit(1)
        print(f'🔀 Checking out {infra_branch} in existing repo...')
        if infra_branch_cfg != 'auto':
            run(['git', '-C', str(infra_path), 'fetch', '--all'])
            run(['git', '-C', str(infra_path), 'checkout', infra_branch])

    # 2) Run the Infra installer (it will create & activate its venv)
    print('🛠️  Installing Hailo Apps Infra...')
    infra_args = [
        str(infra_path / 'install.py'),
        '--config', str(Path(args.config)),
        '--apps-infra-path', str(infra_path),
    ]

    if cfg.get('infra_download_all', True):
        infra_args.append('--all')
    else:
        infra_args.extend([
            '--group', cfg.get('infra_group', 'default'),
        ])

    if cfg.get('infra_resources_config'):
        infra_args.extend([
            '--resources-config', cfg['infra_resources_config'],
        ])
    

    # Call it with the *system* Python; the infra script will re-exec into its venv
    run([sys.executable] + infra_args)

    # 3) Install any extra requirements into the newly created venv
    venv_name = cfg.get('virtual_env_name', 'rpi_examples_venv')
    venv_path = Path(venv_name)
    venv_pip = venv_path / 'bin' / 'pip3'

    extra_reqs = cfg.get('extra_requirements', [])
    if extra_reqs:
        print(f'📦 Installing extra requirements: {extra_reqs}')
        run([str(venv_pip), 'install'] + extra_reqs)

    # 4) Install this RPI Examples package
    print('🛠️  Installing RPI Examples package...')
    #run([str(venv_pip), 'install', '-e', '.'])

    print('✅ RPI Examples setup complete.')

if __name__ == '__main__':
    main()
