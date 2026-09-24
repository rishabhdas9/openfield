# Openfield retrieval benchmark

> Development benchmark on a frozen 16-question set; not a held-out public claim.

| Mode | Recall hop 1 | Recall hop 2 | Recall hop 3 | Abstention | Citations | Median ms | P95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| vector | 1.000 | 0.875 | 0.833 | 1.000 | 1.000 | 0.233 | 0.554 |
| hybrid-graph | 1.000 | 0.875 | 0.833 | 1.000 | 1.000 | 0.359 | 1.010 |

Recommended default: **vector**.

Questions: 16; top-k: 6; model/API cost: $0.
Local model preparation and query embedding: 222.631 ms.
Corpus: 14 chunks, digest `12e2994349a3d3d598739589e60e63fc0962048652f472b9f44a3d97434f3f73`.
Git commit: `bba15aa038579136afeac38bc1a340d23530cd71`; Python: 3.13.15; Openfield: 0.1.0.
