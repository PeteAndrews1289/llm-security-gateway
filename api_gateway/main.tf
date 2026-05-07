provider "aws" {
  region = "us-east-2" # Using your preferred Ohio region
}

# 1. IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "llm_gateway_lambda_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Attach basic execution permissions so Lambda can write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# 2. Package the Python Code and Dependencies into a ZIP
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../lambda_firewall"
  output_path = "lambda_function.zip"
}

# 3. The Serverless Proxy (AWS Lambda)
resource "aws_lambda_function" "llm_firewall" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "llm_security_firewall"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.10"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 30 # LLMs can take a few seconds to respond


  # Securely pass the API key into the Lambda environment
  environment {
    variables = {
      OPENAI_API_KEY = var.openai_api_key
    }
  }
}

# Variable to hold our sensitive API key
variable "openai_api_key" {
  description = "OpenAI API Key for the Lambda function"
  type        = string
  sensitive   = true
}

# 4. The Chokepoint (AWS API Gateway)
resource "aws_apigatewayv2_api" "gateway" {
  name          = "llm-security-gateway"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.gateway.id
  name        = "$default"
  auto_deploy = true

  # --- PHASE 5: EXPLICIT ROUTE RATE LIMITING ---
  # Target the specific route to ensure AWS enforces the throttle
  route_settings {
    route_key              = "POST /chat"
    throttling_burst_limit = 2
    throttling_rate_limit  = 1
  }
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id             = aws_apigatewayv2_api.gateway.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.llm_firewall.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "post_prompt" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# 5. Security: Explicitly allow API Gateway to trigger the Lambda
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.llm_firewall.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.gateway.execution_arn}/*/*"
}

# 6. Output the final public URL to the terminal
output "api_gateway_url" {
  value = "${aws_apigatewayv2_api.gateway.api_endpoint}/chat"
}