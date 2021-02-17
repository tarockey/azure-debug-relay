# a file to test pipeline debugging things
from publish_pipeline import create_and_publish_pipeline


def main():
    """
    CLI entry point
    """
    published_pipeline, aml_workspace = create_and_publish_pipeline()

    experiment_name = "debug_experiment"

    published_pipeline.submit(aml_workspace, experiment_name)

    # TODO: Add listener here


if __name__ == '__main__':
    main()