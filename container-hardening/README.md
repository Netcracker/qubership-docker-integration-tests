# Container Hardening Tests

A self-contained component that verifies Kubernetes container security hardening
rules **CH1–CH12** for pods in a namespace. It is designed to be deployed as a
Helm chart that runs a single Robot Framework Job after every `helm install` or
`helm upgrade`. If any hardening violation is found the Job exits with a non-zero
code, which causes Helm to mark the release as failed.

## Contents

```
container-hardening/
├── docker/Dockerfile                  # Extends BDI; published as
│                                      # ghcr.io/netcracker/qubership-docker-integration-tests-hardening
├── docker-transfer/Dockerfile         # FROM scratch — packages the Helm chart
│                                      # for CI consumption
├── helm/container-hardening/          # Helm chart
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── job.yaml                   # post-install,post-upgrade hook Job
│       ├── serviceaccount.yaml
│       ├── role.yaml                  # pods: get, list
│       ├── rolebinding.yaml
│       └── _helpers.tpl
└── robot/tests/container_hardening/
    └── container_hardening.robot      # Generic Robot suite
```

## Rules checked

| Rule | Description |
|------|-------------|
| CH1  | `runAsNonRoot: true` and `runAsUser != 0` |
| CH2  | `privileged: false` and `allowPrivilegeEscalation: false` |
| CH3  | `hostPID`, `hostIPC` absent or false |
| CH4  | `readOnlyRootFilesystem: true` |
| CH5  | `capabilities.drop` contains `ALL`; no `capabilities.add` |
| CH6  | `seccompProfile.type: RuntimeDefault` |
| CH7  | No `Bidirectional` volume mount propagation |
| CH8  | No forbidden container ports (17–995, 1080, 1236, …) |
| CH9  | Container image must include a tag |
| CH10 | `hostNetwork` absent or false |
| CH11 | No `hostPath` volumes |
| CH12 | No secrets exposed via `env.valueFrom.secretKeyRef` or `envFrom.secretRef` |

## Quick start

```bash
helm install container-hardening ./helm/container-hardening \
  --namespace my-namespace
```

To filter by component and skip specific rules:

```bash
helm install container-hardening ./helm/container-hardening \
  --namespace my-namespace \
  --set containerHardening.partOf="kafka,kafka-services" \
  --set containerHardening.exclusions._all=CH12 \
  --set 'containerHardening.exclusions.kafka-cruise-control=CH4'
```

## Deployment parameters

### `containerHardening`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `containerHardening.image` | string | `ghcr.io/netcracker/qubership-docker-integration-tests-hardening:main` | Test runner image |
| `containerHardening.partOf` | string | `""` | Comma-separated `app.kubernetes.io/part-of` values to filter pods. Empty = all pods in the namespace |
| `containerHardening.exclusions` | map | `{}` | Per-component rule exclusions. Key is `app.kubernetes.io/name` (or `_all` for every pod), value is comma-separated rule IDs (e.g. `CH4, CH11`) |
| `containerHardening.ttlSecondsAfterFinished` | int | `120` | How long Kubernetes keeps the finished Job before auto-deletion |
| `containerHardening.resources.requests.memory` | string | `128Mi` | Memory request |
| `containerHardening.resources.requests.cpu` | string | `100m` | CPU request |
| `containerHardening.resources.limits.memory` | string | `256Mi` | Memory limit |
| `containerHardening.resources.limits.cpu` | string | `200m` | CPU limit |

### Global / platform

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `global.securityContext` | object | `{}` | Extra fields merged into the pod `securityContext` (applied to every workload) |
| `PAAS_PLATFORM` | string | `""` | Set to `KUBERNETES` to add `runAsUser: 1000` / `runAsGroup: 1000` to the pod securityContext. Leave empty for OpenShift (UIDs managed by SCCs) |
| `PART_OF` | string | `container-hardening` | Value of the `app.kubernetes.io/part-of` label applied to all chart resources |
| `ARTIFACT_DESCRIPTOR_VERSION` | string | `""` | Version label stamped on all resources by CI at release time |

### Exclusions examples

```yaml
# Skip CH12 globally and CH4 for one specific component
containerHardening:
  exclusions:
    _all: CH12
    my-service-cruise-control: "CH4, CH11"
```

## How it works

1. Helm installs the chart as a `post-install,post-upgrade` hook with `backoffLimit: 0`.
2. The Job pod runs `run-robot-without-ttyd` (the BDI entrypoint mode that runs Robot and exits with its exit code).
3. The Robot suite calls `Check Container Hardening` from `PlatformLibrary`.
4. `PlatformLibrary` lists all pods in the namespace (filtered by `PART_OF` when set), inspects each pod and container spec, and raises `AssertionError` on any violation.
5. A non-zero exit code marks the Helm hook — and therefore the release — as failed.
6. The Job is cleaned up automatically after `ttlSecondsAfterFinished` seconds.

## Security posture of the Job itself

The Job pod is fully hardened:

- `runAsNonRoot: true`, `seccompProfile: RuntimeDefault`
- `runAsUser: 1000` / `runAsGroup: 1000` (when `PAAS_PLATFORM=KUBERNETES`)
- `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`
- Two `emptyDir` volumes: `/opt/robot/output` (256 Mi) and `/tmp` (64 Mi)
- RBAC: namespaced `Role` with `pods: get, list` only
