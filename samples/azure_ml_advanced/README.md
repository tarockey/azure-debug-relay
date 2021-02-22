# Debugging Advanced Azure Machine Learning Pipelines

This sample demonstrates how to debug a pipeline with [ParallelRunStep](https://docs.microsoft.com/en-us/python/api/azureml-pipeline-steps/azureml.pipeline.steps.parallelrunstep?view=azure-ml-py).

To make sure we only debug it on a single node, we check that `AZ_BATCH_IS_CURRENT_NODE_MASTER` environment variable equals `true`.

When switching between steps and therefore between servers, your local debugging session in VS Code will disconnect. Start the same one (`Python: Listen 5678`) as soon as possible, before another server tries to connect (with Azure ML you usually have a minute or so).

## Configuration

Create an environment or set the following environment variables:

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
* `DEFAULT_DEBUG_CONNECTION_NAME` - default Azure Relay Hybrid Connection to use for debugging.

## How to run

1. Start debugging with `Python: AML Adv 2 Listeners` configuration.
1. Run `python3 samples/azure_ml_advanced/remote_pipeline_demo.py --is-debug true --debug-relay-connection-name <hybrid-connection-name>`
in terminal **on the same machine**. Here **hybrid-connection-name** is a name of Azure Relay Hybrid Connection which Azure Relay Shared Access Policy above has `Listen` and `Send` permissions on.
