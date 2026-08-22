# P0-7 computational/scalability headline results

Reference condition: p=20, n_train=n_cal=n_unlabeled=n_test=1000, mean shift severity 1.0; 5 sequential single-thread repetitions.

| Method | Total median | Ratio/local fit | Inference | Fresh peak RSS delta |
|---|---:|---:|---:|---:|
| SCP-Ridge | 1.723 ms | 0 | 0.104 ms | 0.539 MB |
| Oracle-WCP-Ridge | 2.099 ms | 0 | 0.262 ms | 0.910 MB |
| uLSIF-WCP-Ridge | 32.206 ms | 27.588 ms | 0.369 ms | 5.242 MB |
| Estimated-WCP-Logistic | 53.634 ms | 34.338 ms | 0.331 ms | 8.156 MB |
| RLCP-Ridge | 115.670 ms | 72.642 ms | 41.713 ms | 7.207 MB |
| HGB-WCP-Ridge | 181.340 ms | 168.907 ms | 0.472 ms | 3.934 MB |
| KMM-CP-Ridge | 255.874 ms | 253.512 ms | 0.378 ms | 24.301 MB |
| CQR-GBR | 1.304 s | N/A | 2.511 ms | 1.980 MB |

- Estimated-WCP-Logistic total-runtime dimension exponent: 1.444; p=5 to p=100 runtime ratio: 71.8x.
- KMM ratio/localization-fit calibration-size exponent: 0.856; n=250 to 1500 ratio: 4.30x.
- RLCP inference test-size exponent: 0.546; n_test=250 to 5000 ratio: 5.03x.
- Fresh-process p=100 Estimated-WCP-Logistic peak-RSS delta is about 171 MB.
- Absolute times are environment-specific; empirical exponents describe only the frozen finite grids.
