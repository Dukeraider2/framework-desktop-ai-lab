# Coral Inference Gateway

**Status:** Proposed architecture / not yet implemented  
**Target host:** Promethean OPS-M (exact hardware and PCIe compatibility still subject to validation)  
**Accelerator:** Google Coral Edge TPU, intended M.2 A+E-key module  
**Primary client:** Frigate NVR on the OPS-M  
**Additional clients:** Framework Desktop AI Max+ 395 and NAS-hosted applications

## Purpose

Use the Coral installed locally in the Promethean OPS-M as a shared, LAN-accessible inference resource. Frigate will use it for camera object detection. Other trusted lab systems should be able to submit image-analysis jobs on demand, such as locating faces in a photo collection and returning match metadata so the requesting system can organize files.

The Coral is an accelerator, not a remotely attachable PCIe device. Clients will call a network service; they will not see a virtual TPU or install a device driver.

## Proposed topology

```text
                    Trusted LAN / tailnet
  +-----------------------+       +-----------------------+
  | Framework Desktop     |       | NAS / Immich / tools  |
  | AI Max+ 395           |       | Image library         |
  | Job orchestration,    |       |                       |
  | review, file moves    |       | Calls inference API   |
  +-----------+-----------+       +-----------+-----------+
              |                               |
              +---------------+---------------+
                              |
                       HTTPS / API
                              |
                  +-----------v-----------+
                  | Promethean OPS-M      |
                  |                       |
                  | Inference gateway     |
                  | - authentication      |
                  | - request validation  |
                  | - queue / arbitration |
                  | - model registry      |
                  | - metrics / logging   |
                  |           |           |
                  |     Coral runtime     |
                  |           |           |
                  |     M.2 Coral TPU     |
                  |                       |
                  | Frigate NVR           |
                  | - camera ingest       |
                  | - video decode        |
                  | - recording           |
                  | - event management    |
                  +-----------------------+
```

This is a logical target design, not a claim that the gateway, API, or Frigate integration currently exists.

## Workload boundaries

### 1. Frigate object detection

Frigate is the first integration and the primary workload. Frigate has a built-in Edge TPU detector and documents PCIe/M.2 device selection as `device: pci`. The Coral model must be compatible with the Edge TPU compiler/runtime. Begin with Frigate's documented model and detector configuration, then verify the actual device is detected on this OPS-M.

Official references:
- [Frigate object detectors](https://docs.frigate.video/configuration/object_detectors/)
- [Frigate hardware guidance](https://docs.frigate.video/frigate/hardware/)

### 2. On-demand image analysis

The Framework or NAS should be able to submit bounded jobs, for example:
- Detect faces in a supplied image or batch.
- Return bounding boxes, confidence scores, and image/job identifiers.
- Optionally compare detected faces against an enrolled gallery, if a separately validated embedding and matching pipeline is available.
- Return candidate file paths or identifiers to the caller.

The caller should retain responsibility for file organization. The service returns structured results; the Framework/NAS reviews them and performs any moves or copies. Default behavior must be non-destructive: dry-run results first, explicit approval before filesystem changes, and no arbitrary server-side path access.

**Important capability boundary:** face detection and face recognition are different tasks. A Coral-compatible face detector may be feasible, but face embeddings, identity matching, clustering, and gallery search require their own model/runtime validation. Do not assume an arbitrary face-recognition model can run on the Edge TPU. If a model cannot be compiled for the Edge TPU, perform that stage on the Framework AI Max or CPU rather than forcing it onto the Coral.

### 3. Immich / NAS integration

Treat Immich integration as a later adapter project. Do not assume Immich can directly use this custom Coral API as a drop-in machine-learning backend. First document the Immich machine-learning integration contract and then build and test an adapter if the interfaces permit it.

## Device ownership and concurrency

A key architectural decision remains open: whether Frigate talks directly to the Coral while other clients use a separate service, or whether one gateway process owns the Coral and serves every client.

Do not assume two independent processes can safely share one Edge TPU concurrently. The initial implementation should use one clearly defined device owner and a serialized or explicitly scheduled request queue. Frigate's camera-detection latency must take priority over batch photo jobs. If Frigate's supported integration cannot route through the gateway without fragile modifications, keep Frigate on its native local detector and defer shared access until a supported arbitration design is proven.

Frigate documents a ZMQ detector interface for external detector processes. Investigate whether it can be used as the Frigate adapter, but do not label it a supported Coral-sharing solution until a working prototype demonstrates it.

## API design target

Proposed versioned API, subject to implementation review:

- `GET /health` — service and accelerator health.
- `GET /v1/capabilities` — supported tasks, models, input limits, and runtime versions.
- `POST /v1/jobs/face-detect` — submit face-detection work.
- `POST /v1/jobs/object-detect` — submit supported object-detection work.
- `GET /v1/jobs/{job_id}` — retrieve status and results.
- `GET /metrics` — restricted operational metrics.

Prefer job submission for batches. Set limits for image size, batch size, queue depth, execution time, and retention. Return structured JSON with model/version metadata and confidence values. Avoid returning identity labels unless an explicit, separately secured recognition stage is implemented.

## Security and privacy

- Bind the service to a trusted LAN interface; do not expose it directly to the public internet.
- Require authentication for every inference request.
- Restrict access with firewall rules and, where appropriate, tailnet ACLs.
- Use TLS for traffic crossing untrusted network segments.
- Validate MIME type, dimensions, payload size, and decoded image format.
- Treat images and face data as sensitive. Do not retain submitted images by default.
- Do not log image bytes, face crops, embeddings, or personally identifying labels.
- Keep API credentials and private network details out of Git.
- Keep file movement on the NAS/Framework client side, with dry-run and approval controls.

## Phased implementation and acceptance gates

1. **Hardware identification:** confirm exact OPS-M board, M.2 keying, slot wiring, BIOS behavior, and Linux support. Physical fit alone does not prove PCIe connectivity.
2. **Local Coral validation:** install the correct host driver/runtime for the chosen M.2 device; confirm enumeration and run Google's/Frigate's known-good Edge TPU test.
3. **Frigate baseline:** deploy Frigate on the OPS-M, configure the native Coral detector, and measure inference latency, camera detection FPS, CPU use, and video decode behavior.
4. **Gateway prototype:** implement health/capability endpoints, authentication, bounded job queue, one supported Edge TPU model, and structured results.
5. **Concurrency test:** establish a safe single-owner model and prove Frigate priority under simultaneous camera and batch-image load.
6. **Framework client:** submit a directory of test images, receive face boxes/results, and generate a reviewable dry-run sorting manifest. No automatic moves in the first version.
7. **NAS / Immich adapter:** investigate the supported integration contract and implement only after a compatibility test.
8. **Operations:** add service supervision, logs without image content, metrics, backup of configuration/model metadata, and documented recovery.

A phase is complete only when its acceptance test is recorded with hardware/software versions and observed results.

## Current unknowns

- Exact Promethean OPS-M motherboard/board revision and M.2 slot electrical wiring.
- Whether the selected M.2 Coral module is detected by the OPS-M firmware and Linux kernel.
- Host OS and driver/runtime compatibility for the M.2 Coral.
- Exact Frigate version and whether its current ZMQ detector interface can support the intended shared-device ownership model.
- Edge TPU-compatible face detection model and any separate embedding/matching model.
- Immich adapter feasibility.

## Project principles

- Verify official documentation before installation commands.
- One change at a time; inspect output before proceeding.
- Do not claim hardware or model compatibility until tested.
- Keep the NVR functional even if optional remote inference services are unavailable.
- Prefer explicit APIs and documented contracts over pretending the TPU is a network-attached device.
