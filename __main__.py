import pulumi
import pulumi_aws as aws
import pulumi_archive as archive

schemas = ["hi.txt", "what.txt"]
config = pulumi.Config()
env = config.get("project:environment")

lambda_ = archive.get_file(type="zip",
    source_file="./lambdas/worker/index.py",
    output_path="lambda_function_payload.zip")

worker_manual = aws.lambda_.Function(
    resource_name='worker-manual',
    args=aws.lambda_.FunctionArgs(
        name='worker-manual',
        runtime='python3.9',
        role="arn:aws:iam::052848974346:role/delete-me-elisabeth",
        handler='lambda_function.lambda_handler2',
        source_code_hash=lambda_.output_base64sha256,
        code=pulumi.FileArchive("lambda_function_payload.zip"),
    )
)
