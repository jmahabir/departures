# Solari Board v2 — Setup Guide

## Files
| File | Purpose |
|------|---------|
| `app.py` | Flask backend — API, send form, message storage |
| `display.html` | Solari flip-board display page |
| `solari-board.conf` | Apache virtual host config |
| `solari-board.service` | systemd service (auto-start on boot) |

## Deploy to Pi

### 1. Copy files
```bash
sudo mkdir -p /var/www/solari-board
# Copy all four files there via FE Explorer or scp, then:
sudo chown -R www-data:www-data /var/www/solari-board
```

### 2. Install dependencies
```bash
sudo apt update
sudo apt install -y python3-flask gunicorn
```

### 3. Apache proxy modules
```bash
sudo a2enmod proxy proxy_http
sudo systemctl restart apache2
```

### 4. Apache site
```bash
sudo cp solari-board.conf /etc/apache2/sites-available/
sudo a2ensite solari-board
sudo a2dissite 000-default
sudo systemctl reload apache2
```

### 5. systemd service
```bash
sudo cp solari-board.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable solari-board
sudo systemctl start solari-board
```

### 6. Check it's running
```bash
sudo systemctl status solari-board
```

## URLs
| URL | What it does |
|-----|-------------|
| `http://<pi-ip>/` | Flip-board display |
| `http://<pi-ip>/send` | Post a message |
| `http://<pi-ip>/api/message` | JSON API (used by display) |

## Handy commands
```bash
sudo systemctl restart solari-board      # restart app
sudo journalctl -u solari-board -f       # live logs
sudo chown -R www-data:www-data /var/www/solari-board  # fix permissions after copying files
```
