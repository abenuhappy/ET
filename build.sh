#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# 데이터베이스 초기화
python -c "from app import _init_db; _init_db()"
