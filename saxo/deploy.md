# Nasadenie token infra (Docker / systemd)

Tento dokument popisuje postup nasadenia token refresher-a a token proxy na server (droplet).

Obsahuje tri odporúčané možnosti:

- Docker Compose — rýchle, izolované a ľahko aktualizovateľné nasadenie (odporúčané pre test/dev).
- Docker Compose + systemd — autoštart celej zostavy po reboote (odporúčané pre droplet/produkciu).
- systemd — jednoduché natívne nasadenie bez Dockeru (iba vybrané skripty mimo kontajnerov).

---

## Predpoklady

- Skripty v repozitári: `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/token_daemon.py` a `droplets/conare/var02/token_proxy.py`.
- V priečinku `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/` sú `Dockerfile` a `docker-compose.yml` (repo obsahuje pripravené súbory).
- Na serveri je nainštalovaný Docker + Docker Compose (ak ideš touto cestou) alebo Python 3 + pip (pre systemd).
- Citlivé údaje (SAXO_CLIENT_ID a SAXO_CLIENT_SECRET) nikdy necommituj do repozitára. Použi `.env`, Docker secrets alebo správcu tajomstiev.

---

## Docker Compose — rýchly štart

1) Presuň sa do adresára s `docker-compose.yml`:

```bash
cd /cesta/k/repozitaru/pc/PC/OpenAIGPT/SaxoAPI/Testovanie
```

2) Skopíruj `.env.example` na `.env` a uprav ho:

```bash
cp .env.example .env
# uprav .env: nastav SAXO_CLIENT_ID a SAXO_CLIENT_SECRET
chmod 600 .env
```

3) Spusti Compose (build + run):

```bash
docker compose up -d --build
```

4) Overenie:

- Zisti bežiace služby:

```bash
docker compose ps
```

- Sledu logy daemona:

```bash
docker compose logs -f saxo-token-daemon
```

- Otestuj token proxy (ak v compose expose port 8080):

```bash
curl http://localhost:8080/token
```

5) Zastavenie a odstránenie:

```bash
docker compose down
```

Bezpečnostné poznámky pre Docker:

- Ak nechceš, aby bol token proxy dostupný z internetu, odstráň `ports:` z definície služby v `docker-compose.yml`. V takom prípade bude dostupný len z vnútornej Docker siete.
- Alternatíva: umiestni `token-proxy` za reverzný proxy (napr. nginx) s TLS a autentifikáciou.

---

## Docker Compose + systemd — autoštart celej zostavy

Tento režim spustí celú zostavu (token-daemon live-reader, token-proxy-live-reader, positions-store, positions-ingestor, webapp) automaticky po štarte servera.

Predpoklady:

- Docker + Docker Compose nainštalované a funkčné.
- Systémová služba bude používať compose súbor v `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml`.

Kroky:

1) Skopíruj repozitár na server a umiestni ho do `/opt/saxo` (odporúčané):

```bash
sudo mkdir -p /opt/saxo
# buď rsync
sudo rsync -a --delete /cesta/k/repozitaru/ /opt/saxo/
# alebo git clone priamo do /opt/saxo
```

2) Priprav `.env` pre compose:

```bash
cd /opt/saxo/pc/PC/OpenAIGPT/SaxoAPI/Testovanie
cp .env.example .env
chmod 600 .env
# nastav SAXO_CLIENT_ID, SAXO_CLIENT_SECRET a prípadné REDIRECT_URI
```

3) Nainštaluj systemd unit pre autoštart:

```bash
sudo cp /opt/saxo/deploy_release/saxo-stack.service /etc/systemd/system/
sudoedit /etc/systemd/system/saxo-stack.service  # skontroluj cesty k docker-compose.yml
sudo systemctl daemon-reload
sudo systemctl enable --now saxo-stack.service
```

4) Over beh a logy:

```bash
systemctl status saxo-stack
docker compose -f /opt/saxo/pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml ps
docker compose -f /opt/saxo/pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml logs -f
```

5) Aktualizácie/restarty:

```bash
cd /opt/saxo
sudo git pull --rebase  # alebo rsync novej verzie
sudo docker compose -f pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml build --pull
sudo systemctl restart saxo-stack
```

6) Zastavenie/odstránenie:

```bash
sudo systemctl disable --now saxo-stack
sudo docker compose -f /opt/saxo/pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml down -v
sudo rm -f /etc/systemd/system/saxo-stack.service
sudo systemctl daemon-reload
```

Prvé získanie tokenu (iba raz):

- Pri prvom nasadení potrebuješ získať `refresh_token`. Môžeš použiť make ciele (ak je `make` k dispozícii):

```bash
make -C /opt/saxo auth-url-live-reader   # vypíše autorizačnú URL – otvor ju v prehliadači
make -C /opt/saxo init-live-reader       # výmena kódu za tokeny (postupuje interaktívne)
```

- Alebo priamo cez Docker Compose (bez make):

```bash
docker compose -f /opt/saxo/pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml \
	run --rm saxo-token-daemon-live-reader python /app/test_oauth_min.py --auth-url

# potom vlož presmerovanú URL s ?code=... (REDIRECT_URI musí sedieť s nastavením v Saxo)
docker compose -f /opt/saxo/pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml \
	run --rm saxo-token-daemon-live-reader python /app/test_oauth_min.py --redirect-url "https://tvoja-redirect-host/?code=...&state=..."
```

Poznámka k bezpečnosti:

- `token-proxy` je štandardne dostupný len v rámci internej siete Compose, pokiaľ v `docker-compose.yml` nepoužiješ `ports:`. Na prístup z internetu použi reverzný proxy s TLS a autentifikáciou.
- `webapp` a `positions-store` otvárajú porty; zváž firewall a prípadne reverzný proxy.

## Nasadenie pomocou systemd (bez Dockeru)

Použi tento postup, ak nechceš spúšťať kontajnery.

1) Vytvor Python virtualenv a nainštaluj závislosti (ako deploy používateľ):

```bash
python3 -m venv /opt/saxo/venv
source /opt/saxo/venv/bin/activate
pip install --no-cache-dir requests
deactivate
```

2) Skopíruj skripty na server (príkladný priečinok `/opt/saxo`):

```bash
sudo mkdir -p /opt/saxo
sudo chown $USER:$USER /opt/saxo
cp -r /cesta/k/repozitaru/pc/PC/OpenAIGPT/SaxoAPI/Testovanie /opt/saxo/
cp /cesta/k/repozitaru/droplets/conare/var02/token_proxy.py /opt/saxo/
```

3) Vytvor systemd unit súbor `/etc/systemd/system/saxo-token-daemon.service`:

```ini
[Unit]
Description=Saxo token refresher
After=network.target

[Service]
User=youruser
WorkingDirectory=/opt/saxo/Testovanie
EnvironmentFile=/etc/default/saxo_token
ExecStart=/opt/saxo/venv/bin/python3 /opt/saxo/Testovanie/token_daemon.py --interval 60 --margin 120
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

4) Vytvor environment file `/etc/default/saxo_token` a chráň ho právami 600:

```bash
SAXO_CLIENT_ID=...
SAXO_CLIENT_SECRET=...
TOKENS_FILE=/var/lib/saxo/tokens_min.json
```

5) Priprav priečinok pre tokeny a nastav práva:

```bash
sudo mkdir -p /var/lib/saxo
sudo touch /var/lib/saxo/tokens_min.json
sudo chown youruser:youruser /var/lib/saxo/tokens_min.json
sudo chmod 600 /var/lib/saxo/tokens_min.json
sudo chown root:root /etc/default/saxo_token
sudo chmod 600 /etc/default/saxo_token
```

6) Aktivuj a spusti službu:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now saxo-token-daemon.service
sudo journalctl -u saxo-token-daemon -f
```

Token proxy môžeš spustiť ako samostatný systemd service alebo ho nasadiť za nginx. Odporúčam proxy chrániť autentifikáciou alebo pustiť len cez unix socket alebo vnútornú sieť.

---

## Zhrnutie zmien v repozitári (čo som upravil)

- `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/test_oauth_min.py` — opravené chyby, pridaná `--manual` možnosť, PKCE podpora, bezpečné atomické ukladanie tokenov a čítanie `TOKENS_FILE` z prostredia.
- `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/token_daemon.py` — nový skript, ktorý pravidelne kontroluje TTL tokenu a vykonáva refresh.
- `droplets/conare/var02/token_proxy.py` — jednoduchý HTTP endpoint `GET /token` vracajúci `access_token` a `expires_at`.
- `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/Dockerfile` — jednoduchý obraz pre token daemon.
- `pc/PC/OpenAIGPT/SaxoAPI/Testovanie/docker-compose.yml` — opravený a prepisaný; obsahuje služby a zdieľaný volume `tokens-data`.
- `webapp/`, `positions_store.py`, `live_read_status.py` — pridané časti pre ukladanie a zobrazovanie pozícií (store + web UI + ingestor).
- `deploy_release/saxo-stack.service` — systemd unit na autoštart celej Docker Compose zostavy.
- Dokumentácia: `droplets/conare/var02/README.md`, `proxy_README.md`, `deploy.md` (tento súbor bol práve preložený a rozšírený).

Všetky citlivé hodnoty sú štandardne čítané z prostredia — nepíšu sa do repozitára. Token súbory sa ukladajú atomicky a s právami 600.

---

## Môžem to nasadiť na droplet? (odpoveď a postup)

Áno — môžeš nasadiť oba spôsoby. Odporúčam Docker Compose, pretože zabezpečuje izoláciu a jednoduchú aktualizáciu.

Krátky postup (Docker):

1. Nainštaluj Docker a Docker Compose na droplet.
2. Sklonuj repozitár alebo skopíruj potrebné súbory na server.
3. V adresári `Testovanie/` vytvor `.env` s `SAXO_CLIENT_ID` a `SAXO_CLIENT_SECRET` (práva 600).
4. Spusti `docker compose up -d --build`.
5. Over logy a endpoint `curl http://localhost:8080/token`.

Ak chceš, môžem to pre teba spustiť v tomto dev-containeri (potrebujem platné hodnoty `SAXO_CLIENT_ID` a `SAXO_CLIENT_SECRET` nastavené ako environment pre beh), alebo:

- pripraviť systemd unit a pomocné skripty na nasadenie na droplet, ktoré môžeš zkopírovať a spustiť.

Napíš, či chceš, aby som teraz:

1) spustil `docker compose up -d --build` tu (v dev-containeri),
2) alebo pripravil hotový systemd balík a inštalačný skript pre droplet.
