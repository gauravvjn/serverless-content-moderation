# Serverless Content Moderation System

## Objective:
The system will process user-generated image uploads, moderate the content for objectionability, resize the images if 
needed, and store the results for access and analysis. The proposed system should aim to be robust, modular, and scalable, 
leveraging the designated AWS services effectively to handle varying loads and requirements.


## Architecture Components:
1. API Gateway: Users will submit their image uploads through RESTful API endpoints.
2. AWS Lambda: These functions will handle the processing logic.
3. DynamoDB: This will store metadata about each image, including upload info and moderation results.
4. Amazon S3: This will be used to store the original and processed images.
5. AWS Step Functions: This will coordinate the sequence of processing steps.
6. Lambda Layer: This will provide common libraries or tools across different Lambda functions.
7. Monitoring (CloudWatch): This will monitor and log the system events and function executions.
8. IAM Role: This will ensure that all components have the necessary permissions to access the required resources.


## Detailed Workflow:
1. Image Upload:
    * User uploads an image file via an API Gateway POST endpoint.
    * The API Gateway triggers a Lambda function (`UploadHandler`) that saves the image to an S3 bucket and logs the 
      event to DynamoDB indicating the upload status.
2. Image Processing via Step Functions:
    * Trigger a Step Function from the UploadHandler Lambda function once the image is saved successfully.
    * The Step Function organizes the workflow using the following steps:
        * Content Moderation: Call a Lambda function (`ModerateContent`) that checks the image for any inappropriate content using a machine learning model or a third-party API. The result (pass or fail) along with any flags or labels is stored in DynamoDB.
        * Condition Check: If the content passes moderation, proceed to the next step; otherwise, end the workflow and update the status in DynamoDB.
        * Image Resizing: A Lambda function (`ResizeImage`) is triggered if the image size exceeds a certain threshold or needs to be resized based on usage criteria (Lambda Layer can be used for image processing libraries).
3. Completion:
    * Update the DynamoDB with the final status of the process (moderated and resized if applicable).
    * Store the resized image back to a different S3 bucket or folder.
4. Monitoring and Notifications:
    * Use AWS CloudWatch to monitor all Lambda executions, Step Function state transitions, and log any errors or important information.
    * Set up alerts based on error patterns or execution anomalies.


#### Refer to [Api Doc](/api_doc.md) for API usage, table schema, and system behavior on different outcomes.
