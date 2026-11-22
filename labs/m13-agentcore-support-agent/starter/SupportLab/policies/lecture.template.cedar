permit (
  principal is AgentCore::IamEntity,
  action in [
    AgentCore::Action::"support___getOrder",
    AgentCore::Action::"support___createTicket"
  ],
  resource == AgentCore::Gateway::"GATEWAY_ARN"
);
