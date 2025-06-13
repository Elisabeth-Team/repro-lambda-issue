import pulumi
import pulumi_aws as aws

schemas = ["hi.txt", "what.txt"]

config = pulumi.Config()
env = config.get("project:environment")
print(env)
worker = aws.lambda_.Function(
    resource_name='worker',
    args=aws.lambda_.FunctionArgs(
        name='worker',
        runtime='python3.9',
        role="arn:aws:iam::052848974346:role/delete-me-elisabeth", # from elsewhere
        handler='lambda_function.lambda_handler2',
        code=pulumi.asset.AssetArchive({
            '.': pulumi.asset.FileArchive('./lambdas/worker'),
            'config.yml': pulumi.asset.FileAsset(f'./configs/config.yml'),
            ** {
                f'schemas/{file_name}': pulumi.asset.FileAsset(f'./schemas/{file_name}')
                for file_name in schemas
            }
        })
    )
)