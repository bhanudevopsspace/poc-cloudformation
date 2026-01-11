import json

def handler(event, context):
    """
    Simple Lambda function handler
    """
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Hello from Lambda!',
            'event': event
        })
    }
