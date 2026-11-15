# Source register (reviewed 2026-11-14)

- AMD official Naples NUMA guide: https://docs.amd.com/api/khub/documents/jaFw_nTkeRTQli9mnxl7GQ/content
- AMD EPYC 7001 HPC tuning guide: https://www.amd.com/content/dam/amd/en/documents/epyc-technical-docs/tuning-guides/2018-amd-epyc-7001-tg-hpc-56420.pdf
- Linux kernel CPU isolation docs: https://docs.kernel.org/admin-guide/cpu-isolation.html
- Linux kernel THP docs: https://docs.kernel.org/admin-guide/mm/transhuge.html
- Ubuntu Server CPU affinity/NUMA docs: https://ubuntu.com/server/docs/explanation/performance/perf-tune-affinity-numa/
- Ubuntu 26.04 release notes: https://documentation.ubuntu.com/release-notes/
- llama.cpp CMake options: https://github.com/ggml-org/llama.cpp/blob/master/ggml/CMakeLists.txt
- llama.cpp server options/API: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- llama.cpp benchmark tool: https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/llama-bench.cpp
- GGML Q4_K/Q5_K audit: `docs/ZEN1_GGML_AUDIT.md`. Its source review did not capture a commit SHA, and upstream may have changed. **Pin and re-audit before modifying code.**
- Existing AI lab engineering governance: https://github.com/Dukeraider2/framework-desktop-ai-lab/blob/main/docs/engineering/README.md
