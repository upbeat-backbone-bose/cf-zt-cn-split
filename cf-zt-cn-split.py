import requests
import os
import re

CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ACCOUNT_ID   = os.getenv("CF_ACCOUNT_ID")
PROFILE_ID   = os.getenv("CF_PROFILE_ID", "")
MODE         = os.getenv("MODE", "exclude")  # exclude=CN直连 | include=只有CN走WARP

if not all([CF_API_TOKEN, ACCOUNT_ID]):
    raise ValueError("缺少环境变量！请在 GitHub Secrets 设置 CF_API_TOKEN、CF_ACCOUNT_ID")

HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

MAX_RULES = 4000

# 方案B：gaoyifan 按运营商分列，只取三大运营商，覆盖率 >95%
OPERATOR_URLS = {
    "chinatelecom": "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/chinatelecom.txt",
    "chinaunicom":  "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/chinaunicom.txt",
    "chinamobile":  "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/chinamobile.txt",
}

# 方案A（备用）：IPdeny 聚合版
# IP_URL = "https://www.ipdeny.com/ipblocks/data/aggregated/cn-aggregated.zone"

# DOMAIN_URL = "https://raw.githubusercontent.com/felixonmars/dnsmasq-china-list/master/accelerated-domains.china.conf"


def get_cn_cidrs_by_operator():
    """合并三大运营商 CIDR，去重后返回"""
    cidrs = []
    for name, url in OPERATOR_URLS.items():
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        lines = [line.strip() for line in r.text.splitlines() if line.strip() and not line.startswith('#')]
        print(f"   {name}: {len(lines)} 条")
        cidrs += lines
    unique = list(set(cidrs))
    print(f"   去重后共 {len(unique)} 条")
    return unique


# def get_cn_cidrs():
#     """方案A（备用）：从 IPdeny 拉取聚合后的 CN CIDR 列表"""
#     r = requests.get(IP_URL, timeout=30)
#     r.raise_for_status()
#     return [line.strip() for line in r.text.splitlines() if line.strip() and not line.startswith('#')]


# def get_cn_domains():
#     r = requests.get(DOMAIN_URL, timeout=30)
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
    ip_entries = [{"address": cidr, "description": "CN IP"} for cidr in cidrs[:MAX_RULES]]

    # 暂不合并域名，待配额充足后启用：
    # domain_entries = [{"host": domain, "description": "CN Domain"} for domain in domains[:MAX_RULES]]
    # routes = (ip_entries + domain_entries)[:MAX_RULES]
    routes = ip_entries

    if len(cidrs) > MAX_RULES:
        print(f"⚠️  CIDR 共 {len(cidrs)} 条，超出限制，已截断至 {MAX_RULES} 条")

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
    print("🔄 拉取最新 CN geo 数据（三大运营商）...")
    cidrs = get_cn_cidrs_by_operator()
    print(f"   最多取前 {MAX_RULES} 条上传")

    # domains = get_cn_domains()
    # print(f"   获取到 {len(domains)} 条域名")

    update_split_tunnels(cidrs)