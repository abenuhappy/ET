#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# 데이터베이스 초기화는 앱 시작 시 자동으로 수행됩니다
# Render Disk는 빌드 시점에 마운트되지 않으므로 여기서 초기화하지 않습니다

