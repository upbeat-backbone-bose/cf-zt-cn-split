import requests
import os
import re

CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ACCOUNT_ID   = os.getenv("CF_ACCOUNT_ID")
PROFILE_ID   = os.getenv("CF_PROFILE_ID", "")  # 留空表示默认策略
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
    ip_entries = [{"address": cidr, "description": "CN IP"} for cidr in cidrs]

    # 暂不合并域名，待配额充足后启用：
    # domain_entries = [{"host": domain, "description": "CN Domain"} for domain in domains[:4000]]
    # routes = (ip_entries + domain_entries)[:8000]
    routes = ip_entries

    # 默认策略不带 PROFILE_ID，自定义策略带 PROFILE_ID
    if PROFILE_ID:
        url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/devices/policy/{PROFILE_ID}/{MODE}"
    else:
        url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/devices/policy/{MODE}"

    resp = requests.put(url, json=routes, headers=HEADERS)
    if resp.status_code in (200, 204):
        print(f"✅ 同步成功！{len(routes)} 条路由 | Mode: {MODE}")
    else:
        print(f"❌ 失败 {resp.status_code}: {resp.text}")
        resp.raise_for_status()


if __name__ == "__main__":
    print("🔄 拉取最新 CN geo 数据...")
    cidrs = get_cn_cidrs()
    print(f"   获取到 {len(cidrs)} 条 CIDR")

    # domains = get_cn_domains()
    # print(f"   获取到 {len(domains)} 条域名")

    update_split_tunnels(cidrs)