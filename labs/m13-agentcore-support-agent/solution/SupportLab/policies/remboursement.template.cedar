permit (
  principal is AgentCore::IamEntity,
  action == AgentCore::Action::"support___createRefund",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input.amountCents <= 5000
};
