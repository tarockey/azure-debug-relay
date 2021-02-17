# Debugging Advanced Azure Machine Learning Pipelines

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
* `DEBUG_CONNECTION_STRING` - Azure Relay Shared Access Policy connection string
(must have `Listen` and `Send` permissions)
* `DEFAULT_DEBUG_CONNECTION_NAME` - default Azure Relay Hybrid Connection to use for debugging.

## How to run

1. Start debugging with `Python: Listen for Advanced AML` configuration.
1. Run `python3 samples/azure_ml_advanced/remote_pipeline_demo.py --is-debug true [--relay_name <hybrid-connection-name>]`
in terminal **on the same machine**. Here **hybrid-connection-name** is a name of Azure Relay Hybrid Connection which Azure Relay Shared Access Policy above has `Listen` and `Send` permissions on.
