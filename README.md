# SpaceAPI Endpoint Client for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

[![Validate](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/validate.yml/badge.svg)](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/validate.yml)
[![Lint](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/lint.yml/badge.svg)](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/lint.yml)

A Home Assistant integration that connects to a [SpaceAPI](https://spaceapi.io/) endpoint, allowing you to monitor and control your hackerspace's open/closed status directly from Home Assistant.

## What is SpaceAPI?

SpaceAPI is a standardized API specification used by hackerspaces, makerspaces, and community workshops worldwide to share real-time information about their space status, including whether they're currently open or closed.

## Features

- 🚪 **Toggle Switch** - Control your space's open/closed status with a single switch
- 🔄 **Real-time Status** - Automatic polling every minute to keep the status up-to-date
- 🔒 **Secure Authentication** - API key-based authentication for protected operations
- ⚡ **Optimistic Updates** - Instant UI feedback with race condition protection
- 🛡️ **Debounce Protection** - Prevents API spam from rapid clicking
- 📝 **Debug Logging** - Comprehensive logging for troubleshooting

## Prerequisites

- Home Assistant 2021.1.0 or newer
- A [SpaceAPI endpoint](https://github.com/q30-space/spaceapi-endpoint) server (v15 specification)
- API key for authentication

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/q30-space/ha-spaceapi-endpoint-client`
6. Select category: "Integration"
7. Click "Add"
8. Find "SpaceAPI Endpoint Client" in the integration list
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page][releases]
2. Extract the `custom_components/spaceapi_endpoint_client` directory to your Home Assistant's `custom_components` directory
3. Restart Home Assistant

## Configuration

### Adding the Integration

1. Go to **Settings** → **Devices & Services**
2. Click the **+ Add Integration** button
3. Search for "**SpaceAPI Endpoint Client**"
4. Enter your configuration:
   - **Host URL**: The base URL of your SpaceAPI endpoint (e.g., `http://localhost:8080`)
   - **API Key**: Your API authentication key

### Configuration Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Host URL | Yes | The base URL of your SpaceAPI server |
| API Key | Yes | Authentication key for POST operations |

## Usage

Once configured, the integration creates a device named "SpaceAPI (your-url)" with a single switch entity called "Space Status".

### Space Status Switch

- **ON** = Space is open 🟢
- **OFF** = Space is closed 🔴

When you toggle the switch:
- **Turning ON** sends a POST request with `{"open": true, "message": "Space was switched on", "trigger_person": "Home Assistant SpaceAPI"}`
- **Turning OFF** sends a POST request with `{"open": false, "message": "Space was switched off", "trigger_person": "Home Assistant SpaceAPI"}`

### Automation Example

```yaml
automation:
  - alias: "Notify when space opens"
    trigger:
      - platform: state
        entity_id: switch.space_status
        to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "The hackerspace is now open!"

  - alias: "Close space at midnight"
    trigger:
      - platform: time
        at: "00:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.space_status
```

## How It Works

### Polling

The integration polls your SpaceAPI endpoint (`/api/space`) every **1 minute** to check the current status of the space.

### State Updates

When you toggle the switch in Home Assistant:

1. **Optimistic Update**: The UI updates immediately for instant feedback
2. **API Call**: A POST request is sent to `/api/space/state`
3. **Wait Period**: 0.5 second delay to allow the API to process the change
4. **Verification**: The integration refreshes the state from the server
5. **Lock Release**: The switch becomes available for new actions

### Race Condition Protection

The integration includes multiple layers of protection:
- **Optimistic state**: Prevents coordinator polling from overriding user actions
- **Operation lock**: Prevents multiple simultaneous API calls from rapid clicking
- **Error recovery**: Automatically reverts to the real state if API calls fail

## Troubleshooting

### Integration Not Showing Up

- Ensure the `manifest.json` has a valid `version` field
- Check that all files are in the correct directory structure
- Restart Home Assistant completely (not just reload integrations)

### Connection Errors

- Verify your SpaceAPI server is running and accessible
- Check that the Host URL is correct (including `http://` or `https://`)
- Ensure there are no firewall rules blocking the connection
- Test the endpoint manually: `curl http://your-server/api/space`

### Authentication Errors

- Verify your API key is correct
- Check that your SpaceAPI server has the correct API key configured
- Look for authentication logs in your SpaceAPI server

### Switch State Not Updating

- Check Home Assistant logs for errors (`Settings` → `System` → `Logs`)
- Verify the SpaceAPI server is responding correctly
- Enable debug logging (see below)

### Debug Logging

To enable detailed logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.spaceapi_endpoint_client: debug
```

Then restart Home Assistant and check the logs for detailed information about API calls and state changes.

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/space` | GET | Retrieve current space status |
| `/api/space/state` | POST | Update space open/closed state |

## Device Information

The integration creates a device with the following information:
- **Name**: SpaceAPI (your-url)
- **Manufacturer**: SpaceAPI
- **Model**: SpaceAPI v15
- **Configuration URL**: Links to your SpaceAPI endpoint

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Built from the [Integration Blueprint][integration_blueprint] template
- Implements the [SpaceAPI v15 specification](https://spaceapi.io/)
- Compatible with [spaceapi-endpoint](https://github.com/q30-space/spaceapi-endpoint) server

## Support

- **Issues**: [GitHub Issues](https://github.com/q30-space/ha-spaceapi-endpoint-client/issues)
- **SpaceAPI Community**: [SpaceAPI Website](https://spaceapi.io/)

---

**Made with ❤️ by [q30.space](https://q30.space) for hackerspaces everywhere**

[integration_blueprint]: https://github.com/ludeeus/integration_blueprint
[releases-shield]: https://img.shields.io/github/release/q30-space/ha-spaceapi-endpoint-client.svg?style=for-the-badge
[releases]: https://github.com/q30-space/ha-spaceapi-endpoint-client/releases
[license-shield]: https://img.shields.io/github/license/q30-space/ha-spaceapi-endpoint-client.svg?style=for-the-badge
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge

