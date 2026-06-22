# Smart Climate Proxy

Smart Climate Proxy is a Home Assistant custom integration that creates a virtual climate entity in front of an existing climate device.

It uses an external room temperature sensor and can adjust the underlying climate device setpoint with configurable tolerances, learning, manual override detection and diagnostic entities.

## Features

- Virtual `climate` entity per room
- External temperature sensor support
- Lower and upper room tolerance
- Dry-run mode: calculate without controlling the real device
- Optional control of the underlying climate device
- Learning table for heat and cool setpoints
- Manual override detection
- Optional forwarding of HVAC, fan, swing and preset mode
- Optional quiet-mode switch
- Diagnostic sensors
- Runtime number and switch entities

## Installation with HACS as custom repository

1. Add this repository to HACS as a custom repository.
2. Category: `Integration`.
3. Install `Smart Climate Proxy`.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration**.
6. Search for **Smart Climate Proxy**.

## Configuration

During setup you select:

- Name
- Underlying climate entity
- External temperature sensor
- Target temperature
- Lower and upper tolerance
- Correction interval
- Setpoint step
- Learning settings
- Manual override detection

Advanced options include forwarding HVAC/fan/swing/preset mode, custom heat/cool setpoint limits and an optional quiet-mode switch.

## Service

### `smart_climate_proxy.reset_learning`

Resets the learned heat/cool setpoint tables.

Optional field:

- `entry_id`: reset only one proxy. If omitted, all proxy learning tables are reset.

## Notes

Preset forwarding is disabled by default. This is useful for air conditioners where presets such as sleep, eco or boost should not be activated automatically.
