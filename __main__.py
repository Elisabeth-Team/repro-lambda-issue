import pulumi
import pulumi_aws as aws

schemas = ["hi.txt", "what.txt"]

config = pulumi.Config()
env = config.get("project:environment")

asset = pulumi.asset.AssetArchive({
           '.': pulumi.asset.FileArchive('./lambdas/worker'),
            'config.yml': pulumi.asset.FileAsset(f'./configs/config.yml'),
            ** {
                f'schemas/{file_name}': pulumi.asset.FileAsset(f'./schemas/{file_name}')
                for file_name in schemas
            }
        })

hash = asset.__hash__()

print(hash)
worker = aws.lambda_.Function(
    resource_name='worker',
    args=aws.lambda_.FunctionArgs(
        name='worker',
        runtime='python3.9',
        role="arn:aws:iam::052848974346:role/delete-me-elisabeth", # from elsewhere
        handler='lambda_function.lambda_handler2',
        source_code_hash="WFYpNzO6uoMXQ6TaqRGAoqgsbINfd6gBykzu+3k0wRI=",
        code=asset
    )
)

pulumi.export("hash1", worker.source_code_hash)

pulumi.export("hash", hash)