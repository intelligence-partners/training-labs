# Red team campaign report (M15 lab, step 7)

Evidence file item of the agent (lesson "Audit"). The measured rate holds only for the model below:
a change of model, version or provider reopens the campaign, with the same scenarios.

- Agent and version:
- Model tested (provider, model id, version):
- D4 classifier model:
- Date of the campaign:
- Repetitions per scenario (N):

| Configuration | Injection rate | Active defenses | References |
| --- | --- | --- | --- |
| Bare agent | baseline: ../.. | prompt policy (D0) | — |
| + separation | ../.. | D1 | AML.M0030 |
| + allowlist, amount | ../.. | D2, D5 | AML.M0028 |
| + filtering | ../.. | D4 | AML.M0015 |
| + confirmation | ../.. | D3 | AML.M0029 |

Legitimate scenarios still working with every defense on: yes / no (details).

Decision: defenses that become mandatory in the golden path for an agent at this risk level:
