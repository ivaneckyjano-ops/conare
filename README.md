# Droplet: conare

## Údaje o droplete

- **Názov (hostname):** Conare
- **IP adresa:** 64.227.125.155
- **Poskytovateľ:** DigitalOcean
- **OS:** Ubuntu 22.04.5 LTS
- **Kernel:** 5.15.0-113-generic
- **CPU:** 1 jadro (DO-Regular)
- **RAM:** 957 MB
- **Disk:** 25 GB (16% využité)
- **Uptime:** 5 dní, 49 minút
- **Virtualizácia:** KVM
- **Časové pásmo:** UTC
- **Počúvajúce porty:** 22 (SSH), 80 (nginx), 8080 (python)
- **Bežiace služby:** nginx, ssh, systemd-resolved, unattended-upgrades, atď.

Prehľad a inštrukcie pre nasadenie služieb na droplet "conare".

## Štruktúra

```
droplets/conare/
├── README.md              # Tento súbor
├── Testovanie/            # Hlavná aplikácia (Docker Compose, skripty)
├── deploy/                # Deployment súbory
│   ├── deploy.sh         # Hlavný deployment skript
│   ├── deploy.md         # Dokumentácia deploymentu
│   ├── token_proxy.py    # Token proxy server
│   └── *.service         # Systemd unit súbory
├── var02/                # Staršie súbory (zachované pre kompatibilitu)
└── config*               # Konfiguračné súbory
```

## Deployment postup

### 1. Priprava (lokálne)
```bash
cd droplets/conare
# Súbory sú už pripravené v repozitári
```

### 2. Sync na droplet
```bash
# Na lokálnom počítači
git add .
git commit -m "Update deployment files"
git push

# Na droplet-e (ak má naklonovaný repo)
cd /path/to/repo/droplets/conare
git pull
```

### 3. Nasadenie na droplet-e
```bash
cd /path/to/repo/droplets/conare/deploy
sudo ./deploy.sh /opt/saxo
```

### 4. Overenie
```bash
cd /opt/saxo/Testovanie
docker compose ps
docker compose logs -f
```

## Poznámky

- Deployment skript očakáva Docker + Docker Compose na droplet-e
- Súbory sa kopírujú do `/opt/saxo`
- Pre produkčné nasadenie použite systemd unit súbory
- Citlivé údaje (SAXO_CLIENT_ID, SAXO_CLIENT_SECRET) nastavte v `.env` súbore

## Git workflow

1. **Lokálne zmeny:** Uprav súbory v `droplets/conare/`
2. **Commit:** `git add . && git commit -m "Update"`
3. **Push:** `git push`
4. **Na droplet-e:** `git pull && cd deploy && sudo ./deploy.sh`

Tento prístup eliminuje problémy s SCP transfermi a umožňuje verzovanie deployment konfigurácií.

## Prehľad
- Účel: Token infra pre Saxo (refresher + HTTP proxy) a voliteľne web UI
- Prostredia: sim (demo) / live
- Hlavné komponenty:
  - token-daemon: pravidelné obnovovanie tokenov
  - token-proxy: HTTP endpoint na vydanie aktuálneho access tokenu
  - webapp (voliteľné): jednoduché UI

## Štruktúra
```
droplets/
└─ conare/
   └─ var02/
      └─ token_proxy.py   # jednoduchý HTTP proxy server
```

Pozn.: Dockerfile a docker-compose sa nachádzajú v `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/` (zdieľané pre všetky droplets). Token proxy skript je lokálny v `droplets/conare/var02/`.

## Porty
- token-proxy demo: 8080 (mapované na hosta podľa compose)
- token-proxy live: 8081 (mapované na hosta podľa compose)
- webapp (voliteľné): 5000
- Ďalšie proxy inštancie (reader/0dte/trader): 8181, 8182, 8183

## Tajomstvá (secrets)
- Pre live role použi `.env` súbory v štýle:
  - `SAXO_ENV=live`
  - `SAXO_CLIENT_ID=...`
  - `SAXO_CLIENT_SECRET=...`
  - `REDIRECT_URI=http://127.0.0.1:8765/callback/<role>`
- Príklady nájdeš v: `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/secrets/live/`
- Necommituj reálne hodnoty do git; súbory maj súkromné (600) na serveri.

## Rýchly štart (odporúčané)
Použi hlavný docker-compose v `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/`:

1) Príprava `.env` (ak používaš demo):
```
cd pc/PC/OpenAIGPT/SaxoAPI/Testovanie
cp .env.example .env
# uprav .env ak treba a nastav práva
chmod 600 .env
```

2) Spustenie demá:
```
docker compose up -d --build token-proxy-demo saxo-token-daemon-demo
```

3) Test proxy:
```
curl http://localhost:8080/token
```

4) Vypnutie:
```
docker compose down
```

## Alternatíva: spustenie len token-proxy (bez webappu)
V `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml` už existujú služby `token-proxy-*` s príkazom:
```
command: ["python3", "/app/droplets/conare/var02/token_proxy.py"]
```
Môžeš spustiť konkrétnu službu napr. reader:
```
docker compose up -d --build token-proxy-live-reader
```
Nezabudni nastaviť `TOKENS_FILE` a mount `./data:/data`, kde daemoni ukladajú tokeny.

## Poznámky
- Odporúčam spúšťať proxy len na vnútornú sieť alebo cez reverzný proxy s TLS a autentifikáciou.
- Pri nasadení na server (droplet) skontroluj firewall pravidlá pre použité porty.