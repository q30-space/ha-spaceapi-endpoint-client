# SpaceAPI Endpoint Client for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

[![Validate](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/validate.yml/badge.svg)](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/validate.yml)
[![Lint](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/lint.yml/badge.svg)](https://github.com/q30-space/ha-spaceapi-endpoint-client/actions/workflows/lint.yml)

A Home Assistant integration that connects to a [SpaceAPI](https://spaceapi.io/) endpoint, allowing you to monitor and control your space's open/closed status directly from Home Assistant.

This is a companion app of [SpaceAPI endpoint](https://github.com/q30-space/spaceapi-endpoint) but will handle also all other spaceapi.json providing methods in read-only mode.

## What is SpaceAPI?

SpaceAPI is a standardized API specification used by hackerspaces, makerspaces, and community workshops worldwide to share real-time information about their space status, including whether they're currently open or closed.

## Features

- 🚪 **Toggle Switch** (optional) - Control your space's open/closed status when an API key is provided
- 🔄 **Real-time Status** - Automatic polling every minute to keep the status up-to-date
- 🔒 **Secure Authentication** (optional) - API key-based authentication for protected operations
- 🔄 **Automatic Fallback** - Automatically falls back to direct JSON endpoint when API server is unavailable (no API key required)
- ⚡ **Optimistic Updates** - Instant UI feedback with race condition protection
- 🛡️ **Debounce Protection** - Prevents API spam from rapid clicking
- 📝 **Debug Logging** - Comprehensive logging for troubleshooting

## Prerequisites

- Home Assistant 2021.1.0 or newer
- A [SpaceAPI endpoint](https://github.com/q30-space/spaceapi-endpoint) server or an url pointing to a spaceapi.json file
- API key for authentication (optional; not required if only monitor the status of the space)

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
   - **Host URL**: The base URL of your SpaceAPI endpoint or direct JSON file URL (check https://directory.spaceapi.io/)
   - **API Key** (optional): Your API authentication key. Provide it to enable switching (write access). Leave empty for read-only monitoring.

### Configuration Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Host URL | Yes | The base URL of your SpaceAPI server or direct JSON endpoint URL. Can be any valid SpaceAPI JSON endpoint (see [SpaceAPI Directory](https://directory.spaceapi.io/) for examples) |
| API Key | No | Optional. Required to enable POST operations (switch control). |

### Behavior With and Without API Key

- Without API key: read-only monitoring. The integration polls and displays your space's current open/closed status; no state changes are sent.
- With API key: read-write control. You can toggle the space state from Home Assistant; the integration will POST updates to your SpaceAPI server.

## Usage

Once configured, the integration creates a device named "SpaceAPI (your-url)" with an entity that reflects your space's current open/closed state. If you provide an API key, a toggle control is available from Home Assistant to change the state.

### Space Status Switch

- This section applies when an API key is configured.

- **ON** = Space is open 🟢
- **OFF** = Space is closed 🔴

When you toggle the switch (with API key configured):
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

The integration polls your SpaceAPI endpoint every **1 minute** to check the current status of the space.

**Primary Endpoint**: The integration first attempts to retrieve data from `/api/space` endpoint.

**Automatic Fallback**: If the `/api/space` endpoint fails (connection error, timeout, etc.) and no API key is provided, the integration automatically falls back to a direct GET request to the `host_url` you configured. This allows the integration to work with:
- Direct SpaceAPI JSON endpoints (e.g., `https://spaceapi.example.com/spaceapi.json`)
- Static JSON files hosted anywhere
- Any URL that returns valid SpaceAPI JSON format

This fallback only activates when:
- No API key is configured (read-only mode)
- The primary `/api/space` endpoint fails with a communication error

If an API key is provided, the fallback is disabled to ensure secure API server communication.

### State Updates

When you toggle the switch in Home Assistant (only when an API key is configured):

1. **Optimistic Update**: The UI updates immediately for instant feedback
2. **API Call**: A POST request is sent to `/api/space/state`
3. **Wait Period**: 0.5 second delay to allow the API to process the change
4. **Verification**: The integration refreshes the state from the server
5. **Lock Release**: The switch becomes available for new actions

### Race Condition Protection

The integration includes multiple layers of protection (when switching is enabled with an API key):
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
- If using direct JSON endpoints, verify the URL returns valid SpaceAPI JSON format
- The integration will automatically fall back to direct `host_url` GET requests when the API server is unavailable (read-only mode only)

### Authentication Errors

- If you're using an API key, verify it is correct
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
| `/api/space` | GET | Retrieve current space status (primary endpoint) |
| `{host_url}` | GET | Fallback: Direct JSON endpoint retrieval (used when `/api/space` fails and no API key is provided) |
| `/api/space/state` | POST | Update space open/closed state (used only when API key is provided) |

## Device Information

The integration creates a device with the following information:
- **Name**: SpaceAPI (your-url)
- **Manufacturer**: q30space
- **Model**: SpaceAPI v15
- **Configuration URL**: Links to your SpaceAPI endpoint

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Built from the [Integration Blueprint][integration_blueprint] template
- Implements the [SpaceAPI v15 specification](https://spaceapi.io/docs/)
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

