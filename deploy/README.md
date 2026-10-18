# 部署辅助配置（xingkongzcj.cloud）

本目录是服务器侧配置的**版本化副本**，由 `deploy.py upload` 同步到 `/opt/studymate/deploy/`，再由下面的命令安装到系统位置。

## 目录说明

| 文件 | 用途 | 服务器位置 |
| --- | --- | --- |
| `nginx/studymate.conf` | HTTP 站点，反代到 `127.0.0.1:8000`（备案前使用） | `/etc/nginx/sites-available/studymate.conf` |
| `nginx/studymate-https.conf` | HTTPS 站点（监听 8443）+ 80 跳转 443，备案后启用 | `/etc/nginx/sites-available/studymate-https.conf` |
| `nginx/stream-split.conf` | 443 按 SNI 分流：域名 → 站点，其余 → SSH-over-TLS | 追加进 `/etc/nginx/nginx.conf` 主配置层 |
| `scripts/studymate-backup.sh` | MySQL + Chroma 备份，保留 7 天 | `/usr/local/bin/studymate-backup.sh` |
| `scripts/studymate-backup.{service,timer}` | 每天 03:30 自动备份 | `/etc/systemd/system/` |

## 当前状态（备案未完成）

- `:80` → nginx → 应用，IP 可直接访问：<http://47.109.147.248/>
- `:443` → **仍是 stunnel（SSH-over-TLS）**，没有动，校园网 SSH 不受影响
- `:8000` → 应用（compose 直接映射，保留作为兜底）

## 备案通过后的切换步骤

前提：安全组已放行 `80`、`443`；域名 A 记录已指向 `47.109.147.248`。

> **⚠️ 关键**：切换会把 stunnel 从 443 挪走，而 SSH 正是走这条隧道。
> **绝不能在 SSH 会话里直接执行**，否则重启 stunnel 的瞬间会掐断自己的连接。
> 必须用 `nohup` 脱离会话运行（或直接在阿里云 Workbench 里跑）。

```bash
# 1) 签证书（HTTP-01；此时域名已可访问）
sudo certbot certonly --nginx -d xingkongzcj.cloud -d www.xingkongzcj.cloud

# 2) 挂上 HTTPS 站点（监听 8443，由 443 分流转发进来）
sudo cp /opt/studymate/deploy/nginx/studymate-https.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/studymate-https.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 3) 切换 443（脱离会话运行，脚本自带校验 + 失败自动回滚）
sudo nohup bash /opt/studymate/deploy/scripts/switch-443.sh >/dev/null 2>&1 &
sleep 15
sudo tail -20 /var/log/studymate-switch-443.log     # 看到「切换成功」即完成

# 4) 启用 80 → https 跳转（先禁用 HTTP 站点，避免同名 server 冲突）
sudo rm -f /etc/nginx/sites-enabled/studymate.conf
sudo cp /opt/studymate/deploy/nginx/studymate-redirect.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/studymate-redirect.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 5) 验证
curl -I https://xingkongzcj.cloud
ssh studymate true && echo "SSH 通道正常"
```

> 注意：Ubuntu 的 nginx 把 stream 编译成动态模块，需要装 `libnginx-mod-stream`。
> 装好后 `/etc/nginx/modules-enabled/50-mod-stream.conf` 会自动 `load_module`，
> 否则 `nginx -t` 会报 `unknown directive "map"`。

### 回滚

```bash
sudo cp /root/studymate-switch-*/nginx.conf   /etc/nginx/nginx.conf
sudo cp /root/studymate-switch-*/ssh-tls.conf /etc/stunnel/ssh-tls.conf
sudo nginx -t && sudo systemctl reload nginx
sudo systemctl restart ssh-tls
```

## 提前签证书（可选，不需要备案）

DNS-01 验证只查 TXT 记录，不需要 80/443 对外可访问：

```bash
sudo certbot certonly --manual --preferred-challenges dns \
  -d xingkongzcj.cloud -d www.xingkongzcj.cloud
```

按提示到阿里云解析添加两条 `_acme-challenge` TXT 记录，验证通过后证书即签发。
缺点是续期同样要手动；**备案通过后建议改用 HTTP-01 自动续期**（`certbot renew` + `systemd timer` 会自动接管）。

## 备份与恢复

```bash
# 手动跑一次
sudo /usr/local/bin/studymate-backup.sh
ls -lh /opt/studymate/backups/

# 恢复 MySQL
gunzip -c /opt/studymate/backups/db-YYYYmmdd-HHMMSS.sql.gz \
  | docker exec -i study_mate_mysql mysql -uroot -p"$(grep MYSQL_PASSWORD /opt/studymate/.env | cut -d= -f2-)" study_mate

# 恢复 Chroma
gunzip -c /opt/studymate/backups/chroma-YYYYmmdd-HHMMSS.tar.gz \
  | docker exec -i study_mate_app tar xzf - -C /data
```
