#!/usr/bin/env python3
"""NCP API 호출기 (ncloud CLI 보조).

배포판 ncloud CLI(1.1.x)는 KVM(g3) 서버용 파라미터(serverImageNo, serverSpecCode)와
getServerSpecList 등을 지원하지 않아 VPC API를 직접 서명 호출한다.

사용:
  python3 ncp.py vserver getServerSpecList regionCode=KR zoneCode=KR-2 serverImageNo=23214590
  python3 ncp.py vpc getVpcList regionCode=KR
  python3 ncp.py raw GET  https://ncr.apigw.ntruss.com/ncr/api/v2/repositories
  python3 ncp.py raw POST https://ncr.apigw.ntruss.com/ncr/api/v2/repositories/<name> '{"bucket":"<bucket>"}'
리스트 파라미터는 펼쳐서 전달: networkInterfaceList.1.networkInterfaceOrder=0

인증키: 환경변수 NCP_ACCESS_KEY / NCP_SECRET_KEY, 없으면 ~/.ncloud/configure [DEFAULT]
"""

import base64
import configparser
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_URL = "https://ncloud.apigw.ntruss.com"


def load_keys() -> tuple[str, str]:
    ak, sk = os.getenv("NCP_ACCESS_KEY"), os.getenv("NCP_SECRET_KEY")
    if ak and sk:
        return ak, sk
    cfg = configparser.ConfigParser()
    cfg.read(Path.home() / ".ncloud" / "configure")
    sec = cfg["DEFAULT"]
    return sec["ncloud_access_key_id"].strip(), sec["ncloud_secret_access_key"].strip()


def request(method: str, url: str, body: str | None = None) -> dict:
    ak, sk = load_keys()
    parsed = urllib.parse.urlsplit(url)
    uri = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    ts = str(int(time.time() * 1000))
    msg = f"{method} {uri}\n{ts}\n{ak}"
    sig = base64.b64encode(hmac.new(sk.encode(), msg.encode(), hashlib.sha256).digest()).decode()
    headers = {
        "x-ncp-apigw-timestamp": ts,
        "x-ncp-iam-access-key": ak,
        "x-ncp-apigw-signature-v2": sig,
        "Content-Type": "application/json; charset=utf-8",
    }
    req = urllib.request.Request(url, data=body.encode() if body else None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read()
            return json.loads(raw) if raw else {"status": res.status}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def call(service: str, action: str, params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode({**params, "responseFormatType": "json"})
    return request("GET", f"{API_URL}/{service}/v2/{action}?{query}")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    if sys.argv[1] == "raw":
        method, url, *body = sys.argv[2:]
        print(json.dumps(request(method, url, body[0] if body else None), ensure_ascii=False, indent=2))
        return
    service, action, *rest = sys.argv[1:]
    params = dict(arg.split("=", 1) for arg in rest)
    print(json.dumps(call(service, action, params), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
