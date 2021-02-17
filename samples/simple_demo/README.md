# Simple remote debugging example

1. Set `AZRELAY_CONNECTION_STRING` and `AZRELAY_CONNECTION_NAME` environment variables
or create `.azrelay.json` configuration file in the workspace/repo directory.
1. Start debugging with `Python: Listen 5678` configuration.
1. Repeat #1 **on a remote machine**.
1. **On that remote machine**, clone this repo, and run `python3 samples/simple_demo/remote_server_demo.py --debug attach`.
