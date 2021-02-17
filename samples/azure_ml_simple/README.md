# Simple Azure Machine Learning debugging example

1. Set `AZRELAY_CONNECTION_STRING` and `AZRELAY_CONNECTION_NAME` environment variables
or create `.azrelay.json` configuration file in workspace/repo directory.
1. Create `config.json` [Azure ML Workspace configuration file](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-configure-environment#workspace)
in this file's or workspace/repo directory.
1. Start debugging with `Python: Listen for AML` configuration.
1. Run `python3 samples/simple_demo/deploy_and_run.py` in terminal **on the same machine**.
It will deploy an AML pipeline, and run it on a remote AML Compute Target.
