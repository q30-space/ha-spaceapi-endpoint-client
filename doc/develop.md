# Tips for developers

## Cut a new release

In the Github repo, go to Actions → “Cut release (sync manifest version)” → Run workflow, enter a version like 0.1.3 or v0.1.3.

The workflow updates custom_components/spaceapi_endpoint_client/manifest.json, commits, tags vX.Y.Z, pushes, and creates the GitHub Release.


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

**Note:** The CI script runs hassfest validation which requires Docker. The devcontainer includes Docker-in-Docker support. If you don't have Docker available when running the CI script, you'll need to rebuild your devcontainer to enable Docker support (the first time after this change).