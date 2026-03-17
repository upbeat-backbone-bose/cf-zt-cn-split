import requests
import os
import re

CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ACCOUNT_ID   = os.getenv("CF_ACCOUNT_ID")
PROFILE_ID   = os.getenv("CF_PROFILE_ID", "default")
MODE         = os.getenv("MODE", "exclude")  # exclude=CN直连 | include=只有CN走WARP

if not all([CF_API_TOKEN, ACCOUNT_ID]):
    raise ValueError("缺少环境变量！请在 GitHub Secrets 设置 CF_API_TOKEN、CF_ACCOUNT_ID")

HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

IP_URL = "https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt"
# DOMAIN_URL = "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf"

def get_cn_cidrs():
    r = requests.get(IP_URL)
    r.raise_for_status()
    return [line.strip() for line in r.text.splitlines() if line.strip() and not line.startswith('#')]

# def get_cn_domains():
#     r = requests.get(DOMAIN_URL)
#     r.raise_for_status()
#     domains = []
#     for line in r.text.splitlines():
#         if line.startswith('server=') and '/114' in line:
#             m = re.search(r'server=/([^/]+)/', line)
#             if m:
#                 d = m.group(1)
#                 if not d.startswith('*.'):
#                     d = f"*.{d}"
#                 domains.append(d)
#     return list(set(domains))

def update_split_tunnels(cidrs):
    # 限制 IP 数量不超过 4000 条
    routes = cidrs[:4000]
    payload = {MODE: routes}

    # 正确的 API 路径
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/devices/policy/{PROFILE_ID}"
    resp = requests.patch(url, json=payload, headers=HEADERS)

    if resp.status_code in (200, 204):
        print(f"✅ 同步成功！{len(routes)} 条 IP 路由 | Mode: {MODE}")
    else:
        print(f"❌ 失败 {resp.status_code}: {resp.text}")
        resp.raise_for_status()

if __name__ == "__main__":
    print("🔄 拉取最新 CN geo 数据...")
    cidrs = get_cn_cidrs()
    print(f"   获取到 {len(cidrs)} 条 CIDR")
    update_split_tunnels(cidrs)
