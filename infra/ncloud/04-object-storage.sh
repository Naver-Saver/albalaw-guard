#!/usr/bin/env bash
# Object Storage 버킷 생성 (S3 호환 API — aws CLI 사용)
#   사전: pip install awscli  /  AWS_ACCESS_KEY_ID·AWS_SECRET_ACCESS_KEY 에 NCP 키 설정
set -euo pipefail
source "$(dirname "$0")/env.sh"
EP=https://kr.object.ncloudstorage.com
export AWS_DEFAULT_REGION=kr-standard
aws --endpoint-url "$EP" s3 mb "s3://$OBJECT_STORAGE_BUCKET" || echo "(이미 있으면 무시)"
# 업로드 원본은 1일 후 자동 삭제 (개인정보 보호)
cat > /tmp/lifecycle.json <<JSON
{"Rules":[{"ID":"expire-uploads","Status":"Enabled","Filter":{"Prefix":"uploads/"},"Expiration":{"Days":1}}]}
JSON
aws --endpoint-url "$EP" s3api put-bucket-lifecycle-configuration --bucket "$OBJECT_STORAGE_BUCKET" --lifecycle-configuration file:///tmp/lifecycle.json
aws --endpoint-url "$EP" s3 ls
