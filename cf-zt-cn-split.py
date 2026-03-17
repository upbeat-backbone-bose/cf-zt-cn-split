import requests
import os

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

MAX_RULES   = 4000
MAX_IPS     = 3000  # gaoyifan china.txt 实际条目数约 3000
MAX_DOMAINS = MAX_RULES - MAX_IPS  # 1000

# 域名：Loyalsoldier 精选直连域名
DOMAIN_URL = "https://raw.githubusercontent.com/Loyalsoldier/surge-rules/release/direct.txt"

# IP：gaoyifan 全运营商聚合版（已验证可用，~3000 条）
IP_URL = "https://raw.githubusercontent.com/gaoyifan/china-operator-ip/ip-lists/china.txt"

# 备用 IP 数据源
# ipverse（当前 404，路径待确认）:
#   https://raw.githubusercontent.com/ipverse/rir-ip/master/country/cn/ipv4-aggregate.txt
# IPdeny aggregated (~2200 条):
#   https://www.ipdeny.com/ipblocks/data/aggregated/cn-aggregated.zone
# metowolf/iplist (~1700 条):
#   https://raw.githubusercontent.com/metowolf/iplist/master/data/special/china.txt


def get_cn_cidrs():
    """从 gaoyifan 拉取全运营商聚合的 CN CIDR 列表"""
    r = requests.get(IP_URL, timeout=30)
    r.raise_for_status()
    cidrs = [line.strip() for line in r.text.splitlines() if line.strip() and not line.startswith('#')]
    print(f"   IP 数据源获取到 {len(cidrs)} 条 CIDR，取前 {min(len(cidrs), MAX_IPS)} 条")
    return cidrs


def get_cn_domains():
    """从 Loyalsoldier/surge-rules 拉取精选 CN 直连域名列表"""
    r = requests.get(DOMAIN_URL, timeout=30)
    r.raise_for_status()
    domains = []
    for line in r.text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # surge-rules direct.txt 格式：DOMAIN-SUFFIX,baidu.com
        if line.startswith('DOMAIN-SUFFIX,'):
            d = line.replace('DOMAIN-SUFFIX,', '').strip()
            if d:
                domains.append(f"*.{d}")
    unique = list(set(domains))
    print(f"   域名数据源获取到 {len(unique)} 条域名，取前 {min(len(unique), MAX_DOMAINS)} 条")
    return unique


def update_split_tunnels(cidrs, domains):
    # 域名规则在前（DNS 层优先命中），IP 规则在后（网络层兜底）
    domain_entries = [{"host":    d,    "description": "CN Domain"} for d    in domains[:MAX_DOMAINS]]
    ip_entries     = [{"address": cidr, "description": "CN IP"}     for cidr in cidrs[:MAX_IPS]]
    routes = domain_entries + ip_entries

    print(f"   域名规则：{len(domain_entries)} 条 | IP 规则：{len(ip_entries)} 条 | 合计：{len(routes)} 条")

    if len(routes) > MAX_RULES:
        print(f"⚠️  规则总数超出限制，已截断至 {MAX_RULES} 条")
        routes = routes[:MAX_RULES]

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
    cidrs   = get_cn_cidrs()
    domains = get_cn_domains()
    update_split_tunnels(cidrs, domains)
