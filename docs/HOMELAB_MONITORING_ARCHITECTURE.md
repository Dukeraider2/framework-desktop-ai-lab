# Proxmox Lab Monitoring and Agent Architecture

**Status:** Proposed design; not yet deployed or verified.
**Scope:** Six CSI nodes running Proxmox, an independent physical monitoring computer, the existing Ubuntu AI PC/model proxy, and a future Hermes multi-agent workflow.

## Purpose

Create a browser-accessible control and observability view for the lab. Reuse Proxmox as the source of truth for virtualization state, add historical metrics only where needed, and eventually let Hermes query approved monitoring information. Keep human approval for code merges and deployment.

## Proposed topology

```text
Administrator browser
        |
        +--------------------> Monitoring computer
        |                       - Web dashboard
        |                       - Proxmox API client
        |                       - Optional Prometheus + Grafana
        |                       - Optional read-only MCP service
        |                                  |
        |                                  | HTTPS / authenticated API
        |                                  v
        +--------------------------> Proxmox cluster
                                      CSI-01 ... CSI-06
                                      VMs and LXC containers

Existing Ubuntu AI PC
        |
        +---- existing model proxy / inference for Hermes agents

Git repository
        |
        +---- source, branches, tests, review history, documentation
```

The monitoring computer is a separate physical machine and does not need to join the Proxmox cluster. It requests information over the management network. The AI PC remains the model-inference host; these roles are distinct.

## Responsibilities

- **Proxmox API:** Node, VM, container, task, and supported resource-state information.
- **Monitoring computer:** Dashboard, collection scheduling, optional metric history, alert evaluation.
- **Prometheus (optional):** Time-series metric collection and storage.
- **Grafana (optional):** Dashboarding and visualizing time-series data.
- **MCP (optional, later):** Narrow, explicitly authorized tools through which Hermes can query selected monitoring information. MCP is an access interface, not a metrics database.
- **Hermes:** Coordinates coding, independent review, tests, and later resource-aware scheduling.
- **Git:** Versioned source of truth for code, branches, tests, and decisions.

Proxmox's API alone may be enough for an initial node/workload status page. For longer-term graphs, richer host/network metrics, or application health, additional collection may be needed. Proxmox reporting a VM as running does not prove the application inside it is healthy.

## Security and reliability principles

1. Start with a dedicated read-only Proxmox API identity/token, limited to required resources and privileges.
2. Never commit passwords, API tokens, private keys, or sensitive network inventories to Git.
3. Do not expose the Proxmox API or dashboard directly to the public internet; restrict access to the trusted management network or a suitably secured remote-access path.
4. Keep MCP read-only initially. Do not let an agent start, stop, reconfigure, or delete workloads in the initial phase.
5. Keep monitoring separate from the measured CSI nodes, while recognizing that lightweight collectors on those nodes still consume some resources.
6. Make errors and stale data visible. Do not treat missing telemetry as proof that a node is healthy.
7. Retain human approval for Git merges and deployments.

## Proposed dashboard views

- Cluster summary: online/offline nodes and current alerts.
- Per-node CPU, memory, storage, and network metrics where available.
- VM/container inventory and state.
- Historical charts once time-series collection is configured.
- Agent inventory and application-level health checks when implemented.
- Alerts for unreachable nodes, resource pressure, and stalled agent workloads.

## Decisions not yet verified

- Spare monitoring machine and its hardware resources.
- Management IPs and reachability of the six nodes.
- Exact Proxmox version/configuration and API permissions.
- Which metrics are available directly and which require collectors.
- Whether Prometheus/Grafana are needed after the first dashboard prototype.
- Hermes/MCP protocol and authentication details.
- Agent placement and capacity limits.

Treat this document as a design proposal, not a record of a deployed system.
