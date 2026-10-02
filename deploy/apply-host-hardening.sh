#!/bin/sh
# Apply the 11.5 host baseline. Safe to re-run.
# Does not close the current session. Confirms key login before reloading sshd.
set -eu

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this as the codespace user (sudo is used for sshd and the firewall)." >&2
  exit 1
fi

install -d -m 750 -o codespace -g codespace /workspaces/jpetrucci49-ft-ai-engineering-2-company-project-monorepo/logs
chmod 775 /workspaces/jpetrucci49-ft-ai-engineering-2-company-project-monorepo

KEY=/home/codespace/.ssh/codespaces.auto
echo "Checking key login before changing sshd..."
ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -p 2222 codespace@127.0.0.1 true

sudo tee /etc/ssh/sshd_config.d/99-healthcore.conf >/dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
EOF
sudo sshd -t
if command -v systemctl >/dev/null 2>&1 && systemctl is-active ssh >/dev/null 2>&1; then
  sudo systemctl reload ssh
elif command -v service >/dev/null 2>&1; then
  sudo service ssh reload
else
  sudo kill -HUP "$(pgrep -x sshd | head -1)"
fi

echo "Checking key login after reload..."
if ! ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new -p 2222 codespace@127.0.0.1 true; then
  echo "Key login failed after reload. Restoring root SSH." >&2
  sudo rm -f /etc/ssh/sshd_config.d/99-healthcore.conf
  sudo sshd -t
  if command -v systemctl >/dev/null 2>&1 && systemctl is-active ssh >/dev/null 2>&1; then
    sudo systemctl reload ssh
  else
    sudo service ssh reload
  fi
  exit 1
fi

sudo iptables -P INPUT ACCEPT
sudo iptables -F INPUT
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 2222 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 2000 -j ACCEPT
sudo iptables -A INPUT -p icmp -j ACCEPT
sudo iptables -P INPUT DROP

sudo ip6tables -P INPUT ACCEPT
sudo ip6tables -F INPUT
sudo ip6tables -A INPUT -i lo -j ACCEPT
sudo ip6tables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo ip6tables -A INPUT -p tcp --dport 2222 -j ACCEPT
sudo ip6tables -A INPUT -p tcp --dport 2000 -j ACCEPT
sudo ip6tables -A INPUT -p ipv6-icmp -j ACCEPT
sudo ip6tables -P INPUT DROP

echo "Host hardening applied. Root SSH is rejected. Inbound allow list: 2222, 2000, loopback."
