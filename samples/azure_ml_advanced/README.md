# Debugging Advanced Azure Machine Learning Pipelines

This sample demonstrates how to debug a pipeline with [ParallelRunStep](https://docs.microsoft.com/en-us/python/api/azureml-pipeline-steps/azureml.pipeline.steps.parallelrunstep?view=azure-ml-py) and with distributed Tensorflow steps using [MPI](https://docs.microsoft.com/en-us/python/api/azureml-core/azureml.core.runconfig.mpiconfiguration?view=azure-ml-py).

With ParallelRunStep, to make sure we only debug it on a single node, we check that `AZ_BATCH_IS_CURRENT_NODE_MASTER` environment variable equals `true`.

With MPIConfiguration, it depends on the distributed training framework. Ultimately, you need identify an instance with **rank equal to zero*.
[Look into this guide](https://azure.github.io/azureml-web/docs/cheatsheet/distributed-training/) to understand how to detect the rank.

For example, in Horovod MPI Tensorflow steps in would be `horovod.tensorflow.rank()` which must be zero.

We debug each step using a separate port (5678, 5679, 5680).
VS Code *compound* configuration `Python: AML Advanced 3 Listeners` starts 3 listeners.
With that, we can even debug 3 simultaneously running nodes,
even though in this sample it is only a matter of convenience.

If you need to debug a distributed step across multiple nodes or processes per node,
you may need to add your own code for picking individual debugging ports for every instance of your training steps. Instead of passing port number as a parameter, steps can choose ports and "reserve" them by [adding an Azure ML Run property](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-manage-runs?tabs=python#tag-and-find-runs) - if a property with a certain name was already added, the port has been utilized and therefore cannot be used.
Multiple processes per node require first starting process to initialize a `DebugRelay` object with a list of ports to connect to.
You may need to employ a shared data structure and a locking mechanism to make sure processes know when DebugRelay
has been already initialized (checking for azrelay process also works).

## Configuration

Create an environment (see `.env.sample`) or set the following environment variables:

* `WORKSPACE_NAME` - Azure Machine Learning Workspace name
(will be created if doesn't exist)
* `TENANT_ID` - Azure Tenant Id
* `SUBSCRIPTION_ID` - Existing Azure Subscription Id (in Azure Tenant above)
* `RESOURCE_GROUP` - Existing Azure Resource Group (in the subscription above)
* `APP_ID` - Azure Active Directory Registered Application Id (Service Principal)
* `APP_SECRET` - Service Principal Password for the App Id above
* `REGION` - An Azure region to create a workspace in (if one doesn't exist)
* `COMPUTE_NAME` - name of Azure Machine Learning Compute Cluster (will be created if doesn't exist)
* `PIPELINE_NAME` - name of an Azure Machine Learning Pipeline to publish
* `DEBUG_GLOBAL_AZRELAY_CONNECTION_STRING` - Azure Relay Shared Access Policy connection string
(must have `Listen` and `Send` permissions)
* `DEBUG_GLOBAL_CONNECTION_SECRET_NAME` - AML Key Vault secret name to store connection string in.

## How to run

1. Start debugging with `Python: AML Advanced 3 Listeners` configuration.
1. Run `python3 samples/azure_ml_advanced/remote_pipeline_demo.py --is-debug true --debug-relay-connection-name <hybrid-connection-name>`
in terminal **on the same machine**. Here **hybrid-connection-name** is a name of Azure Relay Hybrid Connection which Azure Relay Shared Access Policy above has `Listen` and `Send` permissions on.
