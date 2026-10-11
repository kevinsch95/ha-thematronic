# Thematronic JBR-1 for Home Assistant

A custom integration (installable through HACS) that brings the values from the
**Thematronic JBR-1** pellet boiler controller web portal,
[jbr1.thematronic.cz](https://jbr1.thematronic.cz/de/), into Home Assistant.

It signs in to the portal with your normal account and reads the same data the
dashboard shows, every 60 seconds by default. It is **read-only**: it never
changes anything on your boiler.

> Unofficial. Not affiliated with Thematronic s.r.o. The portal has no public
> API, so a change on their side can break this integration.

## What you get

One device, **Thematronic JBR-1**, with an entity for every tile on the web
dashboard:

| Dashboard box | Entities |
|---|---|
| Kessel 1 | Flue gas temperature, boiler flow / return temperature, total and current burn time, fan, pump, flame, fault, safety temperature limiter (STB) |
| Kessel 2 | Flow temperature, heating |
| Außen temp / Modus | Outdoor temperature, summer/winter mode |
| HK 1 / HK 2 | Room temperature, room target (comfort / reduced / stop …) and target temperature, flow temperature, humidity, blocking difference, circuit pump |
| Puffer 1 / Puffer 2 | Top / middle / bottom temperature, transfer pump |
| WW | Hot water temperature, target (stop / eco / comfort), blocking difference, pump |
| Solar | Collector temperature, solar pump |

Entities for parts your installation doesn't use (according to the controller's
hydraulic schema, e.g. `421`) are created **disabled**; enable any of them under
*Settings → Devices & services → Entities*. Values the portal shows as `---`
appear as *unknown*.

Names are available in English, German and Norwegian (Bokmål).

The integration ships its own pellet-stove icon (`brand/`), shown in the
integrations list from Home Assistant 2026.3 onwards.

## Installation

### HACS (recommended)

1. In Home Assistant open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/kevinsch95/ha-thematronic` with type **Integration**.
3. Find **Thematronic JBR-1** in HACS, click **Download**, then restart
   Home Assistant.

### Manual

Copy `custom_components/thematronic` into the `custom_components` folder of
your Home Assistant configuration directory and restart Home Assistant.

## Setup

1. **Settings → Devices & services → Add integration → Thematronic JBR-1**.
2. Enter the e-mail and password you use on jbr1.thematronic.cz.

If you later change your portal password, Home Assistant will show a
*re-authenticate* prompt.

### Options

* **Update interval** – seconds between refreshes (minimum 10, default 60).
* **Raw portal signals** – also create a disabled diagnostic sensor for each of
  the ~150 raw signals the portal exposes (state = what the portal prints,
  attributes = raw value and status). Useful for finding values that aren't on
  the dashboard, such as daily maxima (`max_t_*`).

## How it works

After a normal form login, the dashboard calls a JSON API with the session
cookie. The integration does exactly the same:

1. `POST /api/json/reply/DeviceSignalReload` – ask the portal to fetch fresh
   values from the controller
2. `POST /api/json/reply/DeviceSignal` – read all signals

If the session expires it signs in again automatically.

## Troubleshooting

* **Diagnostics** – *Settings → Devices & services → Thematronic JBR-1 → ⋮ →
  Download diagnostics* gives you all raw signals (login details removed).
* **Debug log** – add to `configuration.yaml`:

  ```yaml
  logger:
    logs:
      custom_components.thematronic: debug
  ```

## Development

The parsing logic (`parser.py`) has no Home Assistant dependency and is tested
against a real portal response:

```bash
python -m unittest discover -s tests -v
```
