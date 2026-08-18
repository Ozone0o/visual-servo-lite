# Security policy

Please report vulnerabilities privately through a GitHub Security Advisory for
this repository, or contact the project maintainers privately through the
repository owner. Do not disclose a public exploit involving robot motion.

Include the affected version, a minimal reproduction, the expected impact, and
safe mitigation details. Remove credentials, robot addresses, logs containing
personal data, and camera data before sharing artifacts.

Luma is a control SDK, not an independent robot safety system. Deployments must
keep the `SafetyGate`, command limits, deadman behavior, and hardware safety
supervisor enabled and must validate transport mappings on the target robot.
