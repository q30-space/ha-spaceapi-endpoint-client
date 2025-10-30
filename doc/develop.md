# Tips for developers

## start HA

Once in the devcontainer execute a local HA instance by executint the script [scripts/develop](../scripts/develop).

## reset HA configuration

For development/testing, use the filesystem approach:
- Delete the .storage directory — removes all integrations and devices:

  `rm -rf config/.storage`

    HomeAssistant will recreate it on next start, and you can test the installation flow again.

- Or delete only the config entries file — removes all integrations but keeps some device history:

    `rm config/.storage/core.config_entries`

- Using the UI is slower but more realistic if you want to test the uninstall flow.

The .storage directory is the fastest way to test the installation step.

## Before push

Run some checks locally with the script [scripts/ci](../scripts/ci) .