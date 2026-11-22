# The HR team's service: one module call gives it a compliant key, bucket,
# log group, role and budget.
module "assistant_rh" {
  source = "../modules/ai-service-baseline"

  service_name        = "assistant-rh"
  team                = "rh"
  cost_center         = "CC-1042"
  data_classification = "confidentiel"
  monthly_budget_usd  = 20
  budget_email        = var.budget_email
  ephemeral           = true # lab: terraform destroy deletes everything, data included
}
