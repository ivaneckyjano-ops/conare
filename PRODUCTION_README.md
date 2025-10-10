# Conare.eu Production Deployment

Tento projekt obsahuje monitoring dashboard pre Saxo trading systém nasadený na conare.eu.

## Architektúra

- **Monitoring Dashboard**: Flask web aplikácia na porte 8082
- **Positions Store**: REST API pre pozície na porte 8090
- **Nginx**: Reverse proxy na portoch 80/443

## Súbory pre nasadenie

1. `docker-compose.prod.yml` - Docker Compose konfigurácia pre produkciu
2. `monitoring/Dockerfile` - Dockerfile pre monitoring dashboard
3. `saxo/Testovanie/Dockerfile.positions` - Dockerfile pre positions store
4. `nginx.conare.conf` - Nginx konfigurácia
5. `deploy.sh` - Deploy script

## Nasadenie

1. **Upload súborov na server** (64.227.125.155):
   ```bash
   scp -r /workspaces/conare/* user@64.227.125.155:/opt/conare/
   ```

2. **Spustite deploy script**:
   ```bash
   ssh user@64.227.125.155
   cd /opt/conare
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

3. **Overte nasadenie**:
   ```bash
   curl http://localhost:8082
   curl http://localhost:8090/positions
   ```

## SSL Konfigurácia

Pre HTTPS pridajte SSL certifikáty do `nginx.conare.conf`:

```nginx
ssl_certificate /path/to/your/certificate.crt;
ssl_certificate_key /path/to/your/private.key;
```

Alebo použite Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d conare.eu -d www.conare.eu
```

## Monitoring

- **Service status**: `docker-compose -f docker-compose.prod.yml ps`
- **Logs**: `docker-compose -f docker-compose.prod.yml logs -f`
- **Restart services**: `docker-compose -f docker-compose.prod.yml restart`

## Aktualizácia

```bash
cd /opt/conare
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## Work Log

### Úspechy
- ✅ Docker Engine + Docker Compose nainštalované na Hetzner serveri (91.98.81.44)
- ✅ Positions Store service funkčný (Flask API na porte 8090, SQLite DB)
  - Ingest pozícií cez POST /ingest (Saxo API formát)
  - Get pozícií cez GET /positions
  - Threshold-based updates (ak cena zmení >0.5%)
- ✅ Jednoduchý hedging skript overený (analyzuje ceny cez yfinance, rozhoduje BUY_PUT/CALL)
- ✅ Docker Compose konfigurácia upravená pre repo súbory
- ✅ Testovanie s viacerými pozíciami (AAPL, GOOGL)

### Neúspechy / Nedokončené
- ❌ Monitoring dashboard service (chýba v GitHub repo, iba lokálne)
- ❌ Reálne pripojenie na SaxoTraderGo API
  - OAuth vyžaduje lokálny beh (redirect URI localhost)
  - Pokusy o lokálny OAuth zlyhali (možno nesprávny CLIENT_SECRET alebo OS issues)
  - Tokeny nie sú získané
- ❌ Hedging skript neintegrovaný s Saxo API (iba simulácia)
- ❌ Žiadne web UI (iba API endpointy)

### Poznámky
- Systém funguje pre demo simuláciu bez reálnych API volaní
- Pre live trading potrebuje dokončiť OAuth a pridať Saxo API volania do hedging skriptu
- Positions store je production-ready, hedging logika overená
- Repo má iba základné súbory, lokálne sú extra (monitoring, hedging-calculator)

### Ďalšie kroky pre dokončenie
1. Dokončiť OAuth lokálne, získať tokeny
2. Preniesť tokeny na server
3. Upraviť hedging skript na volanie Saxo API (place orders)
4. Pridať monitoring dashboard (commitnúť do repo)
5. Testovať live trading s malými objemami