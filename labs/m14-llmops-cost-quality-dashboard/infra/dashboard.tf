# Step 8: the dashboard, built from tableau.json.tftpl.

resource "aws_cloudwatch_dashboard" "agent_support" {
  dashboard_name = "m14-agent-support"
  dashboard_body = templatefile("${path.module}/tableau.json.tftpl", {
    region           = var.region
    model_id_observe = var.model_id_observe
  })
}
