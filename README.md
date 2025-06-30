## Prevent cross-OS false positives on lambda updates

Because of some operating system level configurations, the lambda function resource will often detect changes even when none have been made. These changes can show up on `pulumi preview` and `pulumi update` and cause false positives.

This example provides a workaround where a OS-neutral zip file is created and passed to the lambda. The generated .zip is added to the .gitignore to avoid unnecessary clutter of the repo but since it's generated the same on all operating systems, no change is detected on `pulumi preview` or `pulumi up` unless there's been an actual change to the content of the code.
