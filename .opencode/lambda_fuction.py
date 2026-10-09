import json
import os
import base64
import boto3  # type: ignore[import-not-found]
import urllib3

http = urllib3.PoolManager()

# AWS Environment Variables
GEMMA_ENDPOINT = os.environ.get("GEMMA_ENDPOINT_URL", "http://YOUR_EC2_OR_SAGEMAKER_IP:8000/v1/chat/completions")
DYNAMODB_TABLE = os.environ.get("TABLE_NAME", "CivicActionTickets")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:123456789012:CivicAlerts")

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

def get_s3_image_base64(bucket: str, key: str) -> str:
    response = s3.get_object(Bucket=bucket, Key=key)
    return base64.b64encode(response['Body'].read()).decode('utf-8')

def lambda_handler(event, context):
    # 1. Retrieve S3 object metadata
    record = event['Records'][0]
    bucket_name = record['s3']['bucket']['name']
    object_key = record['s3']['object']['key']

    # 2. Convert uploaded S3 image to Base64 payload
    image_b64 = get_s3_image_base64(bucket_name, object_key)

    # 3. Define Tool Schema for Gemma 4 Function Calling
    tools = [{
        "type": "function",
        "function": {
            "name": "create_civic_ticket",
            "description": "Log an actionable community ticket derived from visual notices, forms, or photos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string", 
                        "enum": ["Public Notice", "Infrastructure Defect", "Welfare Program", "Emergency Alert"]
                    },
                    "title": {"type": "string", "description": "Short descriptive title of the issue/notice"},
                    "summary": {"type": "string", "description": "Plain language explanation for citizens"},
                    "action_steps": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Numbered step-by-step clear instructions for action"
                    },
                    "location": {"type": "string", "description": "Extracted street/ward location"},
                    "deadline": {"type": "string", "description": "ISO date or 'Immediate' or 'N/A'"},
                    "urgency": {"type": "string", "enum": ["Low", "Medium", "High", "Critical"]}
                },
                "required": ["category", "title", "summary", "action_steps", "urgency"]
            }
        }
    }]

    # 4. Construct Gemma 4 Multimodal Payload
    gemma_payload = {
        "model": "google/gemma-4-12b-it",
        "messages": [
            {
                "role": "system",
                "content": "You are CivicLens AI powered by Gemma 4. Analyze public posters, handwritten forms, notices, or defect photos. Convert complex text/visual layout into simple, actionable steps for the community, then execute create_civic_ticket."
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": "Analyze this community artifact, simplify instructions, and invoke create_civic_ticket."}
                ]
            }
        ],
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.1
    }

    # 5. Invoke Gemma 4 Endpoint
    res = http.request(
        'POST',
        GEMMA_ENDPOINT,
        headers={'Content-Type': 'application/json'},
        body=json.dumps(gemma_payload)
    )
    
    gemma_res = json.loads(res.data.decode('utf-8'))
    message = gemma_res['choices'][0]['message']

    # 6. Execute Cloud Tool Outputs
    if "tool_calls" in message:
        for tool_call in message['tool_calls']:
            if tool_call['function']['name'] == "create_civic_ticket":
                args = json.loads(tool_call['function']['arguments'])

                # Save record to AWS DynamoDB
                table = dynamodb.Table(DYNAMODB_TABLE)
                table.put_item(Item={
                    'TicketId': object_key,
                    'Category': args['category'],
                    'Title': args['title'],
                    'Summary': args['summary'],
                    'ActionSteps': args['action_steps'],
                    'Location': args.get('location', 'Unspecified'),
                    'Urgency': args['urgency'],
                    'Deadline': args.get('deadline', 'N/A')
                })

                # Broadcast urgent updates via Amazon SNS
                if args['urgency'] in ['High', 'Critical']:
                    formatted_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(args['action_steps'])])
                    sns.publish(
                        TopicArn=SNS_TOPIC_ARN,
                        Subject=f"[{args['urgency'].upper()}] {args['title']}",
                        Message=f"CIVIC ALERT: {args['summary']}\n\nRequired Action:\n{formatted_steps}\n\nDeadline: {args.get('deadline', 'N/A')}"
                    )

    return {
        'statusCode': 200,
        'body': json.dumps({'status': 'Success', 'ticket_id': object_key})
    }