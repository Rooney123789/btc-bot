# Polymarket Setup — Fix Connection Timeout

If `gamma-api.polymarket.com` times out from your network, use one of these options.

---

## Option A: HTTP/HTTPS Proxy

Many VPNs and proxy services expose an HTTP proxy. Set it before running:

**Windows PowerShell:**
```powershell
$env:POLYMARKET_PROXY = "http://127.0.0.1:7890"   # Replace with your proxy
python test_polymarket.py
```

**Windows CMD:**
```cmd
set POLYMARKET_PROXY=http://127.0.0.1:7890
python test_polymarket.py
```

**Linux/Mac:**
```bash
export POLYMARKET_PROXY="http://127.0.0.1:7890"
python test_polymarket.py
```

Common proxy ports:
- **Clash / V2Ray:** 7890 or 7891
- **Shadowsocks:** 1080 (SOCKS5 — use `socks5://127.0.0.1:1080` if aiohttp supports it)
- **Paid proxies:** Use the URL your provider gives you

---

## Option B: VPN (No Proxy)

Some VPNs route all traffic without exposing a proxy:

1. Connect to a US or unrestricted region.
2. Run: `python test_polymarket.py`
3. If it works, run: `python main.py collect`

---

## Option C: Run on VPS

Deploy to a VPS where Polymarket is reachable (e.g. AWS, DigitalOcean, Hetzner):

```bash
git clone https://github.com/Rooney123789/btc-bot.git
cd btc-bot/btc_bot
pip install -r requirements.txt
python test_polymarket.py   # Should work
python main.py collect
```

---

## Verify

Run the test script:

```powershell
cd "c:\Users\Autobot BTC\btc_bot"
python test_polymarket.py
```

- **SUCCESS** → Run `python main.py collect` to fetch Polymarket data
- **FAILED** → Try a different proxy, VPN, or VPS
