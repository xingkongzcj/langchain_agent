#!/usr/bin/env bash
# 把 443 从「纯 SSH-over-TLS」切换为「SNI 分流」：域名走 nginx HTTPS，其余走 SSH 隧道。
#
# 必须脱离当前会话运行，否则重启 stunnel 会掐断正在使用的 SSH 连接：
#   nohup bash /opt/studymate/deploy/scripts/switch-443.sh >/dev/null 2>&1 &
#   tail -f /var/log/studymate-switch-443.log
#
# 脚本自带校验与自动回滚：任一步失败都会恢复切换前的配置。
set -uo pipefail

LOG=${LOG:-/var/log/studymate-switch-443.log}
exec > >(tee -a "$LOG") 2>&1

STREAM_SRC=/opt/studymate/deploy/nginx/stream-split.conf
NGINX_CONF=/etc/nginx/nginx.conf
STUNNEL_CONF=/etc/stunnel/ssh-tls.conf
BACKUP="/root/studymate-switch-$(date +%Y%m%d-%H%M%S)"
DOMAIN="${DOMAIN:-xingkongzcj.cloud}"

mkdir -p "$BACKUP"
cp "$NGINX_CONF" "$BACKUP/nginx.conf"
cp "$STUNNEL_CONF" "$BACKUP/ssh-tls.conf"
echo "[$(date +%T)] 配置已备份到 $BACKUP"

rollback() {
  echo "[$(date +%T)] 开始回滚..."
  cp "$BACKUP/nginx.conf" "$NGINX_CONF"
  nginx -t && systemctl reload nginx
  cp "$BACKUP/ssh-tls.conf" "$STUNNEL_CONF"
  systemctl restart ssh-tls
  echo "[$(date +%T)] 已回滚到切换前状态（443 重新由 stunnel 占用）"
}

echo "[$(date +%T)] 1/3 stunnel 让出 443，改监听 127.0.0.1:4430"
sed -i 's/^accept  = .*/accept  = 127.0.0.1:4430/' "$STUNNEL_CONF"
systemctl restart ssh-tls
sleep 1
if ! ss -lnt | grep -q ':4430 '; then
  echo "[$(date +%T)] stunnel 未监听 4430"
  rollback
  exit 1
fi

echo "[$(date +%T)] 2/3 nginx 接管 443（SNI 分流）"
if ! grep -q 'studymate_backend' "$NGINX_CONF"; then
  cat "$STREAM_SRC" >> "$NGINX_CONF"
fi
if ! nginx -t; then
  echo "[$(date +%T)] nginx 配置校验失败"
  rollback
  exit 1
fi
systemctl reload nginx
sleep 1

echo "[$(date +%T)] 3/3 验证两条分支"
web_cert=$(echo | openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" 2>/dev/null | openssl x509 -noout -subject || true)
ssh_cert=$(echo | openssl s_client -connect 127.0.0.1:443 2>/dev/null | openssl x509 -noout -subject || true)
echo "  SNI=域名 -> $web_cert"
echo "  无 SNI   -> $ssh_cert"

if echo "$web_cert" | grep -q "$DOMAIN" && echo "$ssh_cert" | grep -q 'studymate-ssh'; then
  echo "[$(date +%T)] 切换成功"
  ss -lntp | grep -E ':(80|443|4430|8443)\b'
  exit 0
fi

echo "[$(date +%T)] 分流验证失败"
rollback
exit 1
