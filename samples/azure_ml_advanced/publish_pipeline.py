# The goal of the script is to create and publish Azure ML pipeline

import sys
import os
from azureml.core import Workspace
from azureml.core.authentication import ServicePrincipalAuthentication
from azureml.exceptions import WorkspaceException
from azureml.core.compute import AmlCompute
from azureml.core.compute import ComputeTarget
from azureml.exceptions import ComputeTargetException
from msrest.exceptions import HttpOperationError
from azureml.core.datastore import Datastore
from azureml.core.runconfig import Environment, CondaDependencies
from azureml.pipeline.core import Pipeline, PublishedPipeline, PipelineData
from azureml.core import RunConfiguration
from azureml.pipeline.core import PipelineParameter
from azureml.pipeline.steps import PythonScriptStep
from azureml.pipeline.steps import ParallelRunStep, ParallelRunConfig
from dotenv import load_dotenv
from azureml.core import ScriptRunConfig
from azureml.core.runconfig import MpiConfiguration

load_dotenv()

# A set of variables that you are required to provide is below.
workspace_name = os.environ.get("WORKSPACE_NAME")
resource_group = os.environ.get("RESOURCE_GROUP")
subscription_id = os.environ.get("SUBSCRIPTION_ID")
tenant_id = os.environ.get("TENANT_ID")
app_id = os.environ.get("APP_ID")
app_secret = os.environ.get("APP_SECRET")
region = os.environ.get("REGION")
compute_name = os.environ.get("COMPUTE_NAME")
pipeline_name = os.environ.get("PIPELINE_NAME")
debug_connection_string = os.environ.get("DEBUG_GLOBAL_AZRELAY_CONNECTION_STRING")
debug_connection_string_secret_name = os.environ.get("DEBUG_GLOBAL_CONNECTION_SECRET_NAME")

def create_and_publish_pipeline() -> any:
    """
    Creates and publish a pipeline
    Returns:
        PublishedPipeline: a reference to just published pipeline
        Workspace: a reference to the Azure ML Workspace
    """
    print("Getting base pipeline objects")
    aml_workspace = get_workspace(workspace_name,
                                  resource_group,
                                  subscription_id,
                                  tenant_id,
                                  app_id,
                                  app_secret,
                                  region,
                                  create_if_not_exist=False)
    print(aml_workspace)

    # putting secrets to keyvault
    aml_workspace.get_default_keyvault().set_secret(
        debug_connection_string_secret_name, debug_connection_string)

    # Get Azure machine learning cluster
    aml_compute = get_compute(aml_workspace, compute_name)

    print(aml_compute)

    batch_conda_deps = CondaDependencies.create(
        conda_packages=[],
        pip_packages=[
            'argparse==1.4.0',
            'azureml-core==1.22.0',
            'debugpy==1.2.1',
            'azure-debug-relay'
        ])
    batch_env = Environment(name="train-env")
    batch_env.docker.enabled = True
    batch_env.python.conda_dependencies = batch_conda_deps


    curated_env_name = 'AzureML-TensorFlow-2.2-CPU'
    tf_env = Environment.get(workspace=aml_workspace, name=curated_env_name)
    tf_env.save_to_directory("env_tf", overwrite=True)

    tf_env = Environment.load_from_directory("env_tf")
    tf_env.name = "traintf"
    tf_env.python.conda_dependencies.add_pip_package('argparse==1.4.0')
    tf_env.python.conda_dependencies.add_pip_package('debugpy==1.2.1')
    tf_env.python.conda_dependencies.add_pip_package('azure-debug-relay')
    
    print("Create pipeline steps")
    steps = get_pipeline(
        aml_compute, aml_workspace.get_default_datastore(), batch_env, tf_env)

    print("Publishing pipeline")
    published_pipeline = publish_pipeline(aml_workspace, steps, pipeline_name)

    print(f"Pipeline ID: {published_pipeline.id}")

    return published_pipeline, aml_workspace


def get_pipeline(aml_compute: ComputeTarget, blob_ds: Datastore, batch_env: Environment, tf_env: Environment) -> str:
    """
    Creates pipeline steps
    Parameters:
        aml_compute (ComputeTarget): a reference to a compute
        blob_ds (DataStore): a reference to a datastore
        batch_env (Environment): a reference to environment object
        tf_env (Environment): a horovod/tf environment
    Returns:
        string: a set of pipeline steps
    """

    # We need something to generate data by the way
    pipeline_files = PipelineData(
        "pipeline_files", datastore=blob_ds).as_dataset()

    # Pipeline parameters to use with every run
    is_debug = PipelineParameter("is_debug", default_value=False)
    debug_port = PipelineParameter("debug_port", default_value=5678)
    relay_connection_name = PipelineParameter(
        "debug_relay_connection_name", default_value="none")

    single_step_config = RunConfiguration()
    single_step_config.environment = batch_env
    single_step = PythonScriptStep(
        name=f"single-step",
        script_name="samples/azure_ml_advanced/steps/single_step.py",
        source_directory=".",
        runconfig=single_step_config,
        arguments=[
            "--pipeline-files", pipeline_files,
            "--is-debug", is_debug,
            "--debug-relay-connection-name", relay_connection_name,
            "--debug-port", debug_port,
            "--debug-relay-connection-string-secret", debug_connection_string_secret_name
        ],
        inputs=[],
        outputs=[pipeline_files],
        compute_target=aml_compute,
        allow_reuse=False
    )

    output_dir = PipelineData("output_dir")

    parallel_run_config = ParallelRunConfig(
        entry_script="samples/azure_ml_advanced/steps/parallel_step.py",
        source_directory=".",
        mini_batch_size="5",
        output_action="summary_only",
        environment=batch_env,
        compute_target=aml_compute,
        error_threshold=10,
        run_invocation_timeout=600,  # very important for debugging
        node_count=2,
        process_count_per_node=1)

    parallelrun_step = ParallelRunStep(
        name="parallel-run-step",
        parallel_run_config=parallel_run_config,
        inputs=[pipeline_files],
        output=output_dir,
        arguments=[
            "--is-debug", is_debug,
            "--debug-relay-connection-name", relay_connection_name,
            "--debug-port", debug_port,
            "--debug-relay-connection-string-secret", debug_connection_string_secret_name
        ],
        allow_reuse=False
    )

    parallelrun_step.run_after(single_step)

    distr_config = MpiConfiguration(process_count_per_node=1, node_count=2)

    src = ScriptRunConfig(
        source_directory=".",
        script="samples/azure_ml_advanced/steps/mpi_step.py",
        arguments=[
            "--input-ds", pipeline_files,
            "--is-debug", is_debug,
            "--debug-relay-connection-name", relay_connection_name,
            "--debug-port", debug_port,
            "--debug-relay-connection-string-secret", debug_connection_string_secret_name
            ],
        compute_target=compute_name,
        environment=tf_env,
        distributed_job_config=distr_config,
    )

    mpi_step = PythonScriptStep(
        name="mpi-step",
        script_name="samples/azure_ml_advanced/steps/mpi_step.py",
        arguments=[
            "--input-ds", pipeline_files,
            "--is-debug", is_debug,
            "--debug-relay-connection-name", relay_connection_name,
            "--debug-port", debug_port,
            "--debug-relay-connection-string-secret", debug_connection_string_secret_name
            ],
        compute_target=aml_compute,
        inputs=[pipeline_files],
        outputs=[],
        runconfig=src.run_config,
        source_directory="."
    )

    mpi_step.run_after(parallelrun_step)

    print("Pipeline Steps Created")

    steps = [
        single_step,
        parallelrun_step,
        mpi_step
    ]

    print(f"Returning {len(steps)} steps")
    return steps


def get_workspace(
    name: str,
    resource_group: str,
    subscription_id: str,
    tenant_id: str,
    app_id: str,
    app_secret: str,
    region: str,
    create_if_not_exist=False,
):
    """
    Returns a reference to a desired workspace
    Parameters:
      name (str): name of the workspace
      resource_group (str): resource group name
      subscription_id (str): subscription id
      tenant_id (str): tenant id (aad id)
      app_id (str): service principal id
      app_secret (str): service principal password
      region (str): location of the workspace
      create_if_not_exist (bool): Default value is False
    Returns:
      Workspace: a reference to a workspace
    """
    service_principal = ServicePrincipalAuthentication(
        tenant_id=tenant_id,
        service_principal_id=app_id,
        service_principal_password=app_secret,
    )

    try:
        aml_workspace = Workspace.get(
            name=name,
            subscription_id=subscription_id,
            resource_group=resource_group,
            auth=service_principal,
        )

    except WorkspaceException as exp_var:
        print("Error while retrieving Workspace...: %s", exp_var)
        if create_if_not_exist:
            print("Creating AzureML Workspace: %s", name)
            aml_workspace = Workspace.create(
                name=name,
                subscription_id=subscription_id,
                resource_group=resource_group,
                create_resource_group=True,
                location=region,
                auth=service_principal,
            )
            print("Workspace %s created.", aml_workspace.name)
        else:
            sys.exit(-1)

    return aml_workspace


def get_compute(workspace: Workspace, compute_name: str, vm_size: str = "Standard_DS3_v2", vm_priority: str = "dedicated", min_nodes: int = 0, max_nodes: int = 4,
                scale_down: int = 600):
    """
    Returns an existing compute or creates a new one.
    Args:
      workspace: Workspace: AzureML workspace
      compute_name: str: name of the compute
      vm_size: str: VM size
      vm_priority: str: low priority or dedicated cluster
      min_nodes: int: minimum number of nodes
      max_nodes: int: maximum number of nodes in the cluster
      scale_down: int: number of seconds to wait before scaling down the cluster
    Returns:
        ComputeTarget: a reference to compute
    """

    try:
        if compute_name in workspace.compute_targets:
            compute_target = workspace.compute_targets[compute_name]
            if compute_target and isinstance(compute_target, AmlCompute):
                print("Found existing compute target %s so using it.", compute_name)
        else:
            compute_config = AmlCompute.provisioning_configuration(vm_size=vm_size,
                                                                   vm_priority=vm_priority,
                                                                   min_nodes=min_nodes,
                                                                   max_nodes=max_nodes,
                                                                   idle_seconds_before_scaledown=scale_down)

            compute_target = ComputeTarget.create(
                workspace, compute_name, compute_config)
            compute_target.wait_for_completion(show_output=True)
        return compute_target
    except ComputeTargetException as ex_var:
        print('An error occurred trying to provision compute: %s', str(ex_var))
        sys.exit(-1)


def get_blob_datastore(workspace: Workspace, data_store_name: str, storage_name: str, storage_key: str,
                       container_name: str):
    """
    Returns a reference to a datastore
    Parameters:
      workspace (Workspace): existing AzureML Workspace object
      data_store_name (string): data store name
      storage_name (string): blob storage account name
      storage_key (string): blob storage account key
      container_name (string): container name
    Returns:
        Datastore: a reference to datastore
    """
    try:
        blob_datastore = Datastore.get(workspace, data_store_name)
        print("Found Blob Datastore with name: %s", data_store_name)
    except HttpOperationError:
        blob_datastore = Datastore.register_azure_blob_container(
            workspace=workspace,
            datastore_name=data_store_name,
            account_name=storage_name,  # Storage account name
            container_name=container_name,  # Name of Azure blob container
            account_key=storage_key)  # Storage account key
    print("Registered blob datastore with name: %s", data_store_name)
    return blob_datastore


def publish_pipeline(aml_workspace, steps, pipeline_name) -> PublishedPipeline:
    """
    Publishes a pipeline to the AzureML Workspace
    Parameters:
      aml_workspace (Workspace): existing AzureML Workspace object
      steps (list): list of PipelineSteps
      pipeline_name (string): name of the pipeline to be published
      build_id (string): DevOps Pipeline Build Id
    Returns:
        PublishedPipeline
    """
    train_pipeline = Pipeline(workspace=aml_workspace, steps=steps)
    train_pipeline.validate()
    published_pipeline = train_pipeline.publish(
        name=pipeline_name,
        description="Model training/retraining pipeline")
    print(
        f'Published pipeline: {published_pipeline.name}')

    return published_pipeline
