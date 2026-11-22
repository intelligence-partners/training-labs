# Step 7: an HTTP API with a Lambda target. The quick create builds the default route and the
# auto-deployed stage. WARNING: no authorizer, the API is public while it exists (lab only).

resource "aws_apigatewayv2_api" "rag" {
  name          = var.lab_name
  protocol_type = "HTTP"
  # TODO (step 7): quick create, set the target to the function ARN (aws_lambda_function.rag.arn).
}

# TODO (step 7): aws_lambda_permission "apigw" with statement_id "apigw-lab", letting
# apigateway.amazonaws.com invoke the function from "${aws_apigatewayv2_api.rag.execution_arn}/*".
