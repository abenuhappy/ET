#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# GitHub에서 data.json 자동 로드 (선택사항)
# 환경 변수 GITHUB_REPO가 설정되어 있으면 앱 시작 시 자동으로 GitHub에서 data.json을 가져옵니다
# 예: GITHUB_REPO=username/repo 또는 GITHUB_REPO=https://raw.githubusercontent.com/username/repo/main

