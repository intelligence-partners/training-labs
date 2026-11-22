forbid (
  principal,
  action == AgentCore::Action::"support___createRefund",
  resource == AgentCore::Gateway::"GATEWAY_ARN"
)
when {
  context.input.orderId like "B2B-*"
};
