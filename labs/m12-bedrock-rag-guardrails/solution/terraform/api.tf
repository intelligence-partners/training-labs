# Step 7: an HTTP API with a Lambda target. The quick create builds the default route and the
# auto-deployed stage. WARNING: no authorizer, the API is public while it exists (lab only).

resource "aws_apigatewayv2_api" "rag" {
  name          = var.lab_name
  protocol_type = "HTTP"
  target        = aws_lambda_function.rag.arn
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "apigw-lab"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rag.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rag.execution_arn}/*"
}
