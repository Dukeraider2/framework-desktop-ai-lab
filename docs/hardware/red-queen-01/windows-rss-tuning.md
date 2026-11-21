# Red Queen 01 — Windows RSS tuning (proposed baseline)

Hardware: AMD Ryzen 7 5800X3D (8 identical Zen 3 cores / 16 logical processors), Windows, Radeon RX 6800 XT. Target: 10GbE NIC; **adapter model and Windows CPU topology must be verified before applying**.

## Goal
Start with four RSS receive queues and up to four RSS processors, favoring the upper-numbered cores for network receive processing. Leave low-numbered cores less occupied by NIC receive DPCs during gaming. RSS is **not** CPU isolation or game-thread pinning.

## Proposed physical cores
Physical cores 4–7, with logical processor IDs **8, 10, 12, 14 only if** Windows topology confirms consecutive SMT sibling numbering (0/1, 2/3, ...). Windows RSS PowerShell parameters do **not** guarantee exact selection of this noncontiguous set. Do not claim that a processor range alone pins RSS to 8,10,12,14.

## Inspect first (Administrator PowerShell)
```powershell
Get-NetAdapter | Format-Table Name, InterfaceDescription, Status, LinkSpeed
Get-NetAdapterRss | Format-List Name, Enabled, NumberOfReceiveQueues, BaseProcessorNumber, MaxProcessorNumber, MaxProcessors, RssProcessorArray, IndirectionTable
```

## Apply a cautious four-processor baseline
Replace `Ethernet` with the **actual 10GbE adapter name** shown above. Requires NIC driver support; RSS settings may briefly interrupt networking.
```powershell
Set-NetAdapterRss -Name 'Ethernet' -Enabled $true -NumberOfReceiveQueues 4 -BaseProcessorGroup 0 -BaseProcessorNumber 8 -MaxProcessorGroup 0 -MaxProcessorNumber 14 -MaxProcessors 4
Get-NetAdapterRss -Name 'Ethernet' | Format-List *
```

Inspect `RssProcessorArray` and `IndirectionTable` after applying. Do not assume Windows uses 8,10,12,14; if it includes SMT siblings or unsupported topology, revisit NIC driver settings and benchmark. If the cmdlet rejects queue counts or processor limits, inspect the supported capabilities rather than forcing them.

## Validation
Benchmark 2 vs 4 queues for throughput (e.g. iperf3), latency/jitter under load, CPU DPC/interrupt load, and game frametime consistency. Revert to prior recorded settings if results regress. Buffer counts and RSS profile are adapter-dependent and intentionally not set here.
