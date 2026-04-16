# lutron-cli

CLI for Lutron Caseta smart lighting control, focused on vacation and departure workflows.

## Installation

```bash
pip install -e .
```

## Setup

1. **Discover your bridge:**
   ```bash
   lutron scan
   ```

2. **Pair with the bridge** (press the small black button on the back when prompted):
   ```bash
   lutron pair 192.168.1.100
   ```
   This saves certificates and sets the bridge as your default.

3. **Verify connection:**
   ```bash
   lutron devices
   ```

## Usage

### Smart Away (vacation mode)
```bash
lutron away          # Check status
lutron away on       # Enable (simulates occupancy)
lutron away off      # Disable
```

### Scenes
```bash
lutron scenes        # List all scenes
lutron scene 3       # Activate scene by ID
```

### Device Control
```bash
lutron devices                  # List all devices
lutron devices --domain light   # List only lights
lutron status 5                 # Check specific device
lutron off 5                    # Turn off device
lutron off 5 --fade 3           # Turn off with 3-second fade
```

### Areas & Occupancy
```bash
lutron areas         # List rooms/areas
lutron occupancy     # Check occupancy sensors
```

### Configuration
```bash
lutron config                        # Show current config
lutron config --host 192.168.1.100   # Set default bridge
```

## Output

All commands output JSON by default, designed for programmatic consumption by the OpenClaw plugin.

## Requirements

- Python 3.10+
- Lutron Caseta Smart Bridge (L-BDG2-WH or similar)
- Network access to the bridge
