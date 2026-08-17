# Public real-data sources and canonical checksums

The repository does **not** redistribute raw UCI datasets. `real_data/code/download_uci_data.py` downloads the official records through `ucimlrepo==0.0.7`; `validate_data.py` applies the frozen schema checks.

| key | UCI ID | rows | predictors | target | canonical SHA-256 |
|---|---:|---:|---:|---|---|
| ccpp | 294 | 9,568 | 4 | PE | `007b39d32b2d7cd8599e8f92be298006b18b216f43a25f23ffa405880d5bdf43` |
| appliances | 374 | 19,735 | 25 | Appliances | `04061f9f449f503768ed370262beb4865a3e4e30c75b0d387cbc7c0140c624b6` |
| superconductivity | 464 | 21,263 | 81 | critical_temp | `f989abf12e4214741b28204b59e7fb9f024ad7c2d11e4c4e3afa74fbb1b6580d` |
| gas_turbine_nox | 551 | 36,733 | 9 | NOX | `811de4b24d263079000733e700d556ab8c3cdc9e8164d50a45e421a428e8cd17` |
| online_news | 332 | 39,644 | 58 | shares | `e70a03997c3e568a39508e39489aea4088e18436f18cbb8139f7f6ace45f53f0` |

## Online News provenance note

UCI metadata reports 39,797 instances, while the official `ucimlrepo==0.0.7` object used by the locked acquisition route returns 39,644 rows. No local row filtering is performed. The 39,644-row canonical artifact is retained and documented in `docs/protocols/real_data_amendment_online_news_row_count.md`.
