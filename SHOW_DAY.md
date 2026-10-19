# Show Day Cheat Sheet — connecting to the Pi from a laptop

Laptop and Pi both join your **phone's hotspot**, then you SSH in from
PowerShell. Do the "Before the show" part at home, while the Pi is
still reachable on your home WiFi.

## Before the show (do once, at home)

### 1. Set up the hotspot on your phone

- **Hotspot name:** make it simple — letters and numbers only, e.g.
  `LucyHotspot`.
  - iPhone names the hotspot after the phone ("Bobby’s iPhone"), and
    that curly apostrophe is a common reason a Pi won't connect.
  - Change it in **Settings → General → About → Name**.
- **Password:** simple too, 8+ characters, no special symbols.
- **iPhone:** turn on **Personal Hotspot → Maximize Compatibility**.
- **Android:** set security to **WPA2** (not WPA3-only) and the band to
  **2.4 GHz**, if those options are offered.

### 2. Teach the Pi the hotspot

SSH into the Pi on home WiFi:

```
ssh admin@HOSTNAME.local
```

Then run the command below. Replace `LucyHotspot` and `PASSWORD` with
your hotspot's real name and password, and keep the quotes.

```
sudo nmcli connection add type wifi con-name show-hotspot ifname wlan0 ssid "LucyHotspot" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "PASSWORD" connection.autoconnect yes connection.autoconnect-priority 10
```

The Pi keeps home WiFi too. It joins whichever known network is
around, preferring the hotspot.

### 3. Test it at home

1. Turn on the phone hotspot.
2. Turn **home WiFi off on the laptop**, and connect the laptop to the
   hotspot.
3. Reboot the Pi:
   ```
   sudo reboot
   ```
4. Wait about a minute, then connect again:
   ```
   ssh admin@HOSTNAME.local
   ```
5. If `.local` doesn't work over the hotspot (common on phone
   hotspots), use the IP address instead — see "Finding the Pi's IP"
   below. Write it down. It usually stays the same on the same phone.

### 4. Pack a backup: an Ethernet cable

Plug the cable straight from the laptop into the Pi; no network is
needed. Then:

```
ssh admin@HOSTNAME.local
```

This usually works with no setup. Test it at home too. Laptops without
an Ethernet port need a USB-to-Ethernet adapter.

## At the show

1. Turn on the phone hotspot **first**, then power on the Pi. If the Pi
   is already on, it rejoins within a minute or so.
2. Connect the laptop to the hotspot.
3. Open **PowerShell**, then connect:
   ```
   ssh admin@HOSTNAME.local
   ```
   or use the IP instead: `ssh admin@192.168.x.x`.
4. Type the password. **Nothing appears as you type**; that's normal.
5. Type `exit` when you're done.

## Finding the Pi's IP

- **Android:** Hotspot settings → Connected devices. Tap the Pi; some
  phones show its IP.
- **iPhone:** iPhone doesn't show IPs. Install **Fing** (free) on the
  phone, scan the network, and look for "Raspberry Pi".
- **From the laptop**, while both are on the hotspot:
  ```
  arp -a
  ```
  Try each listed IP that isn't the phone itself (the phone is usually
  the one ending in `.1`).
  - iPhone hotspots use `172.20.10.x`.
  - Android hotspots often use `192.168.43.x` or similar.

## Handy commands once you're in

| What | Command |
|---|---|
| Restart just the display | `sudo systemctl restart kiosk-display` |
| Restart everything (display, server, button/motion) | `sudo systemctl restart kiosk-server kiosk-display kiosk-gpio` |
| See button/motion events live (Ctrl+C to stop) | `journalctl -u kiosk-gpio -f` |
| Check whether the services are running | `systemctl status kiosk-display kiosk-server kiosk-gpio` |
| Reboot the Pi | `sudo reboot` |
| Shut down safely before unplugging | `sudo shutdown now` |

## Common SSH errors

| Message | Fix |
|---|---|
| `Could not resolve hostname` | `.local` isn't working on this network. Use the IP instead. |
| `Connection timed out` | The Pi isn't on the hotspot yet. Wait a minute, and check the hotspot's connected-device count. |
| `Permission denied` | Wrong username or password (the ones set in Raspberry Pi Imager). |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | Run `ssh-keygen -R HOSTNAME.local` (or `ssh-keygen -R <the IP>`), then connect again. |
