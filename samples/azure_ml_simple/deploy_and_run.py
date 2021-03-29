#pylint: disable=abstract-class-instantiated
import os
import json
import hashlib # for MD5
import azureml.core as amlcore
from azureml.core import Workspace, ComputeTarget, Experiment
from azureml.core.authentication import InteractiveLoginAuthentication
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.core.compute_target import ComputeTargetException
from azureml.core.runconfig import RunConfiguration
from azureml.pipeline.steps import PythonScriptStep
from azureml.pipeline.core import Pipeline, StepSequence


# Connection string for Azure Relay Hybrid Connection
azrelay_connection_string = None
# Hybrid Connection name
azrelay_connection_name = None
# Debugging port
debug_port = 5678

# AML compute cluster or instance name.
cluster_name = "Debug-Std-DS3v2"
# Experiment name
experiment_name = "Debug-Experiment-1"

# If azrelay_connection_string or azrelay_connection_name is None,
# trying to get it from .azrelay.json or environment variables
config_file_name = "./.azrelay.json"
if azrelay_connection_string is None or azrelay_connection_name is None:
    if os.path.exists(config_file_name):
        with open(config_file_name) as cfg_file:
            config = json.load(cfg_file)
            azrelay_connection_name = config["AZRELAY_CONNECTION_NAME"]
            azrelay_connection_string = config["AZRELAY_CONNECTION_STRING"]
    else:
        azrelay_connection_name = os.environ.get("AZRELAY_CONNECTION_NAME")
        azrelay_connection_string = os.environ.get("AZRELAY_CONNECTION_STRING")

if azrelay_connection_string is None or azrelay_connection_name is None:
    print("Azure Relay Hybrid Connection is not configured")
    exit(1)

# load workspace from config.json file
this_script_dir = os.path.dirname(os.path.abspath(__file__))
interactive_auth = InteractiveLoginAuthentication()
try:
    workspace = Workspace.from_config(auth=interactive_auth)
except:
    try:
        config_path = os.path.join(this_script_dir, "config.json")
        workspace = Workspace.from_config(config_path, auth=interactive_auth)
    except Exception as ex:
        print(f"Cannot get a workspace: {ex}")
        exit()

print('Workspace name: ' + workspace.name,
      'Azure region: ' + workspace.location,
      'Subscription id: ' + workspace.subscription_id,
      'Resource group: ' + workspace.resource_group, sep='\n')

# Getting an Azure ML Compute Target
try:
    compute_target = ComputeTarget(workspace=workspace, name=cluster_name)
    print('Found existing compute target')
except ComputeTargetException:
    print('Creating a new compute target...')
    compute_config = AmlCompute.provisioning_configuration(vm_size='STANDARD_D3_V2',
                                                           max_nodes=1)

    # create the cluster
    compute_target = ComputeTarget.create(
        workspace, cluster_name, compute_config)

    # can poll for a minimum number of nodes and for a specific timeout.
    # if no min node count is provided it uses the scale settings for the cluster
    compute_target.wait_for_completion(
        show_output=True, min_node_count=None, timeout_in_minutes=20)

# store the connection string in AML workspace Key Vault
# (secret name is 'debugrelay-' + MD5(azrelay_connection_string) )
hybrid_connection_string_secret =\
    f"debugrelay-{hashlib.md5(azrelay_connection_string.encode('utf-8')).hexdigest()}"
workspace.get_default_keyvault().set_secret(hybrid_connection_string_secret, azrelay_connection_string)

# Configuring a PythonScriptStep with a RunConfiguration
# that includes debugpy and azure-debug-relay
run_config = RunConfiguration()
conda_dependencies = run_config.environment.python.conda_dependencies
conda_dependencies.add_conda_package("pip")
conda_dependencies.add_pip_package("azureml-sdk==" + amlcore.__version__)
conda_dependencies.add_pip_package("debugpy==1.2.1")
conda_dependencies.add_pip_package("azure-debug-relay==0.5.0")

train_step = PythonScriptStep(name='Train Step with Debugging',
                              script_name="samples/azure_ml_simple/steps/train.py",
                              arguments=[
                                  "--debug", "attach",
                                  # passing connection string secret's name, not the connection string itself
                                  "--debug-relay-connection-string-secret", hybrid_connection_string_secret,
                                  "--debug-relay-connection-name", azrelay_connection_name,
                                  "--debug-port", debug_port
                              ],
                              source_directory=".",
                              compute_target=compute_target,
                              runconfig=run_config,
                              allow_reuse=False)

# Submitting an Azure ML Pipeline Run
step_sequence = StepSequence(steps=[train_step])
pipeline = Pipeline(workspace, steps=step_sequence)
experiment = Experiment(workspace=workspace, name=experiment_name)
run = experiment.submit(pipeline)
