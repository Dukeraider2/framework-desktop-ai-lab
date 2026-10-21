# Streaming and Capture Validation

## Intended workflow
Gaming PC HDMI output → capture card HDMI IN → HDMI OUT to display → USB-C to Framework Desktop → OBS Studio on Ubuntu.

Target: 1080p60. Exact UGREEN model is not yet confirmed.

## Validation
1. Identify the model from the label or USB vendor/product IDs.
2. Check the exact model's official UGREEN product page/manual.
3. Inspect enumeration:
   ```bash
   lsusb
   v4l2-ctl --list-devices
   ```
   The second command may require the `v4l-utils` package.
4. Check supported capture formats and frame rates for the relevant V4L2 device.
5. Determine whether audio appears as a separate capture device.
6. Install OBS using its official Linux guidance or a trusted Ubuntu package source.
7. Test preview, audio sync, local recording and HDMI passthrough at 1080p60.
8. Run a sustained local recording before testing a live stream.
9. Record dropped frames, CPU/GPU load, temperature and audio/video sync.

Do not publish stream keys, account tokens, private stream URLs, usernames, desktop notifications or captured personal information. Use a test scene and local recording during validation.