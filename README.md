# cf-zt-cn-split

自动同步中国大陆 IP 段到 Cloudflare Zero Trust 分流隧道（Split Tunnels），实现 CN 流量直连、其余流量走 WARP 的网络分流策略。

---

## 功能简介

- 自动拉取最新中国大陆 IP 数据（来源：[gaoyifan/china-operator-ip](https://github.com/gaoyifan/china-operator-ip) 聚合版）
- 通过 Cloudflare Zero Trust API 更新设备策略的 Split Tunnels 规则
- 支持 `exclude`（CN 直连）和 `include`（仅 CN 走 WARP）两种模式
- 通过 GitHub Actions 定时自动运行，无需手动维护

---

## 工作原理

```
gaoyifan/china-operator-ip (china.txt)
        ↓ 拉取聚合后的 CN CIDR 列表（~3000 条）
cf-zt-cn-split.py
        ↓ 调用 Cloudflare Zero Trust API
设备策略 Split Tunnels 规则（exclude / include）
        ↓
CN 流量直连，其余流量走 WARP
```

---

## 前置要求

- Cloudflare Zero Trust 账户（免费版即可）
- 已在设备上部署 Cloudflare WARP 客户端
- Cloudflare API Token（需具备 Zero Trust 写权限）

---

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将仓库复制到你的 GitHub 账户。

### 2. 配置 GitHub Secrets

进入仓库 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 说明 | 必填 |
|-------------|------|------|
| `CF_API_TOKEN` | Cloudflare API Token，需具备 Zero Trust 写权限 | ✅ |
| `CF_ACCOUNT_ID` | Cloudflare 账户 ID，可在控制台右侧边栏找到 | ✅ |
| `CF_PROFILE_ID` | 设备策略 ID，留空则使用默认策略 | ❌ |
| `MODE` | 分流模式：`exclude`（CN 直连）或 `include`（仅 CN 走 WARP），默认 `exclude` | ❌ |

#### 如何获取 API Token

1. 前往 [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
2. 点击 **Create Token**
3. 选择 **Edit Cloudflare Zero Trust** 模板，或手动添加 `Zero Trust: Edit` 权限
4. 复制生成的 Token

### 3. 启用 GitHub Actions

进入仓库 **Actions** 标签页，启用 Workflow。默认每天自动运行一次，也可手动触发。

---

## 配置说明

### 分流模式（MODE）

| 模式 | 行为 |
|------|------|
| `exclude`（默认） | CN IP 段加入排除列表，CN 流量**不走** WARP，直连出口 |
| `include` | CN IP 段加入包含列表，**只有** CN 流量走 WARP |

大多数用户选择 `exclude` 模式：境外流量走 WARP，国内流量直连，兼顾速度与访问需求。

### 设备策略（PROFILE_ID）

- 留空：更新**默认**设备策略的 Split Tunnels 规则
- 填写策略 ID：更新指定的自定义设备策略

---

## IP 数据源

| 数据源 | 条目数 | 说明 |
|--------|--------|------|
| [gaoyifan/china-operator-ip](https://github.com/gaoyifan/china-operator-ip) `china.txt`（当前使用） | ~3000 条 | 全运营商聚合版，条目少，更新及时 |
| gaoyifan 三大运营商分列（备用） | ~8500 条（去重后） | 电信 + 联通 + 移动，未聚合，条目较多 |
| [17mon/china_ip_list](https://github.com/17mon/china_ip_list)（已弃用） | ~7500 条 | 超出 Cloudflare 4000 条规则上限 |

> **注意**：Cloudflare Zero Trust Split Tunnels 单策略最多支持 **4000 条**规则。

---

## 本地运行

```bash
# 安装依赖
pip install requests

# 设置环境变量
export CF_API_TOKEN="your_api_token"
export CF_ACCOUNT_ID="your_account_id"
export CF_PROFILE_ID=""   # 留空使用默认策略
export MODE="exclude"

# 运行脚本
python cf-zt-cn-split.py
```

正常输出示例：

```
🔄 拉取最新 CN geo 数据（gaoyifan 聚合版）...
   获取到 2985 条 CIDR（最多取前 4000 条）
✅ 同步成功！2985 条路由 | Mode: exclude
```

---

## GitHub Actions 定时任务

默认配置为每天 UTC 02:00（北京时间 10:00）自动运行，也可在 Actions 页面手动触发 **workflow_dispatch**。

如需修改定时频率，编辑 `.github/workflows/` 下的 workflow 文件中的 `cron` 表达式。

---

## 常见问题

**Q：同步成功后 WARP 客户端需要重启吗？**  
A：不需要，Cloudflare Zero Trust 策略更新后会自动下发到已连接的 WARP 客户端。

**Q：报错 `invalid number of rules, number of rules cannot be greater than 4000`？**  
A：IP 数据源条目超出限制，当前使用的 gaoyifan 聚合版通常不会触发此问题。若触发，脚本会自动截断至 4000 条。

**Q：报错 `invalid exclude value`？**  
A：API payload 格式错误，请确保使用最新版本的脚本。

**Q：如何确认规则已生效？**  
A：前往 Cloudflare Zero Trust Dashboard → **Settings → WARP Client → Device settings → 对应策略 → Split Tunnels**，查看规则列表是否已更新。

---

## 许可证

MIT License