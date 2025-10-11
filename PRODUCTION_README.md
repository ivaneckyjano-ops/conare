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
- ✅ **Multi-token architektúra implementovaná (NOVÁ ÚPRAVA)**
  - Oddelené token daemon služby pre demo a live prostredie
  - Automatické obnovovanie tokenov na pozadí
  - Token proxy API na portoch 8080 (demo) a 8081 (live)
  - Paralelný beh demo aj live tokenov bez konfliktu
  - Úplná docker-compose.prod.yml konfigurácia s 5 službami

### Neúspechy / Nedokončené
- ❌ Monitoring dashboard service (chýba v GitHub repo, iba lokálne)
- ⚠️ **Reálne pripojenie na SaxoTraderGo API (PRIPRAVENÉ NA DOKONČENIE)**
  - OAuth vyžaduje lokálny beh (redirect URI localhost)
  - CLIENT_ID a CLIENT_SECRET získané: 2d7a66918b594af5bc2ac830a3b79d2c / 2f5ad858c3eb4ee9b5207d9be5c9c8c5
  - Multi-token architektúra pripravená na demo aj live tokeny
  - Zostáva: dokončiť OAuth proces a preniesť tokeny na server
- ❌ Hedging skript neintegrovaný s Saxo API (iba simulácia)
- ❌ Žiadne web UI (iba API endpointy)

### Poznámky
- Systém funguje pre demo simuláciu bez reálnych API volaní
- **Multi-token architektúra umožňuje simultánny beh demo aj live prostredí**
- Pre live trading potrebuje dokončiť OAuth a pridať Saxo API volania do hedging skriptu
- Positions store je production-ready, hedging logika overená
- Repo má iba základné súbory, lokálne sú extra (monitoring, hedging-calculator)

## Ďalšie kroky
1. **Dokončiť OAuth proces lokálne** (demo alebo live prostredie)
2. **Preniesť získané tokeny na server** do docker-compose služieb
3. **Spustiť multi-token architektúru** na produkcii
4. **Integrovať reálne Saxo API volania** do hedging logiky
5. **Testovať automatické obnovovanie tokenov** na pozadí
### Priebeh a prestávka
 - Dátum: 2025-10-11
 - Stav: Pracovná relácia prerušena (prestávka s deťmi). Všetky zmeny boli uložené na serveri a do GitHub repozitára.
 - Čo je hotové: docker-compose nasadenie spustené, všetky služby postavené a spustené.
 - Nasledujúci krok: dokončiť OAuth flow (lokálne) po návrate.



### Ďalšie kroky pre dokončenie
1. Dokončiť OAuth lokálne, získať tokeny
2. Preniesť tokeny na server
3. Upraviť hedging skript na volanie Saxo API (place orders)
4. Pridať monitoring dashboard (commitnúť do repo)
5. Testovať live trading s malými objemami