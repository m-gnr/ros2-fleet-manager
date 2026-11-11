| Varyant | Koşu | Nav2 S/A | Fiziksel kriter | Temiz kabul | Fiziksel hatalar (m) |
|---|---:|---:|---:|---:|---|
| a-baseline | 3 | 2/1 | 1/3 | 1/3 | 0.343 / 2.827 / 0.484 |
| a-planning-reference | 1 | 1/0 | 1/1 | 1/1 | 0.317 |
| acceptance-pickup | 5 | 5/0 | 5/5 | 5/5 | 0.254 / 0.214 / 0.282 / 0.200 / 0.173 |
| alpha1-002 | 3 | 2/1 | 0/3 | 0/3 | 0.386 / 2.794 / 0.373 |
| alpha3-002 | 1 | 1/0 | 1/1 | 0/1 | 0.303 |
| alpha3-002-repeat | 3 | 1/2 | 1/3 | 1/3 | 0.295 / 2.870 / 2.785 |
| alpha4-0002 | 1 | 1/0 | 1/1 | 0/1 | 0.317 |
| alpha4-0002-repeat | 3 | 3/0 | 3/3 | 3/3 | 0.230 / 0.340 / 0.341 |
| b-landmark | 3 | 3/0 | 1/3 | 1/3 | 0.382 / 0.324 / 0.505 |
| beam-heading0 | 3 | 3/0 | 3/3 | 3/3 | 0.216 / 0.246 / 0.216 |
| beam-headingpi | 3 | 3/0 | 3/3 | 3/3 | 0.244 / 0.179 / 0.235 |
| beam-model | 3 | 3/0 | 3/3 | 3/3 | 0.223 / 0.244 / 0.154 |
| beams180 | 3 | 2/1 | 2/3 | 2/3 | 0.333 / 2.791 / 0.317 |
| c-heading0 | 3 | 3/0 | 1/3 | 1/3 | 0.288 / 0.369 / 0.426 |
| c-headingpi | 3 | 3/0 | 1/3 | 1/3 | 0.377 / 0.319 / 0.368 |
| field-prob | 3 | 3/0 | 2/3 | 2/3 | 0.299 / 0.335 / 0.363 |
| sigma-005 | 3 | 0/3 | 0/3 | 0/3 | 2.966 / 2.866 / 2.969 |
| sigma-010 | 3 | 0/3 | 0/3 | 0/3 | 2.982 / 2.878 / 2.906 |
| sigma-010-replacement | 1 | 0/1 | 0/1 | 0/1 | 2.845 |

| Varyant | Hedef penceresi medyan (sim s) | RTF medyan | Beta AMCL ortalama CPU (%) | Son covariance xx/yy/yaw medyan |
|---|---:|---:|---:|---|
| a-baseline | 24.500 | 0.995 | 2.716 | 0.107 / 0.025 / 0.026 |
| a-planning-reference | 23.930 | 1.000 | 2.570 | 0.062 / 0.016 / 0.028 |
| acceptance-pickup | 25.355 | 0.999 | 3.140 | 0.061 / 0.006 / 0.015 |
| alpha1-002 | 24.750 | 0.998 | 2.690 | 0.074 / 0.015 / 0.011 |
| alpha3-002 | 49.245 | 0.982 | 3.293 | 0.054 / 0.019 / 0.031 |
| alpha3-002-repeat | 31.885 | 0.996 | 2.558 | 0.022 / 0.014 / 0.023 |
| alpha4-0002 | 24.545 | 0.997 | 2.822 | 0.060 / 0.008 / 0.022 |
| alpha4-0002-repeat | 24.050 | 1.000 | 2.600 | 0.039 / 0.011 / 0.023 |
| b-landmark | 23.830 | 0.999 | 2.684 | 0.104 / 0.017 / 0.029 |
| beam-heading0 | 23.040 | 0.999 | 3.078 | 0.132 / 0.006 / 0.016 |
| beam-headingpi | 21.930 | 0.999 | 2.981 | 0.071 / 0.007 / 0.014 |
| beam-model | 25.015 | 0.987 | 3.597 | 0.041 / 0.007 / 0.011 |
| beams180 | 24.550 | 0.999 | 2.676 | 0.063 / 0.015 / 0.028 |
| c-heading0 | 22.435 | 1.000 | 2.678 | 0.089 / 0.016 / 0.032 |
| c-headingpi | 21.050 | 1.000 | 2.558 | 0.068 / 0.015 / 0.022 |
| field-prob | 24.740 | 0.992 | 3.090 | 0.004 / 0.001 / 0.000 |
| sigma-005 | 32.045 | 1.000 | 2.781 | 0.023 / 0.012 / 0.023 |
| sigma-010 | 32.055 | 0.999 | 2.491 | 0.026 / 0.019 / 0.020 |
| sigma-010-replacement | 31.270 | 0.990 | 2.821 | 0.024 / 0.013 / 0.020 |

| Koşu | Nav2 | Fiziksel hata (m) | Map–fiziksel (m) | Yaw hata (rad) | Recovery max | Duruş | Probe / dünya |
|---|---|---:|---:|---:|---:|---|---|
| a-baseline/pickup-1 | 4 | 0.343 | 0.183 | 0.302 | 0 | GEÇTİ | 0 / 0 |
| a-baseline/pickup-2 | 6 | 2.827 | 0.136 | 2.774 | 21 | GEÇTİ | 0 / 0 |
| a-baseline/pickup-3 | 4 | 0.484 | 0.397 | 0.319 | 0 | GEÇTİ | 0 / 0 |
| a-planning-reference/pickup-1 | 4 | 0.317 | 0.090 | 0.278 | 0 | GEÇTİ | 0 / 0 |
| acceptance-pickup/pickup-1 | 4 | 0.254 | 0.096 | 0.237 | 0 | GEÇTİ | 0 / 0 |
| acceptance-pickup/pickup-2 | 4 | 0.214 | 0.056 | 0.237 | 0 | GEÇTİ | 0 / 0 |
| acceptance-pickup/pickup-3 | 4 | 0.282 | 0.067 | 0.251 | 0 | GEÇTİ | 0 / 0 |
| acceptance-pickup/pickup-4 | 4 | 0.200 | 0.043 | 0.222 | 0 | GEÇTİ | 0 / 0 |
| acceptance-pickup/pickup-5 | 4 | 0.173 | 0.066 | 0.232 | 0 | GEÇTİ | 0 / 0 |
| alpha1-002/pickup-1 | 4 | 0.386 | 0.148 | 0.268 | 0 | GEÇTİ | 0 / 0 |
| alpha1-002/pickup-2 | 6 | 2.794 | 0.143 | 2.844 | 21 | GEÇTİ | 0 / 0 |
| alpha1-002/pickup-3 | 4 | 0.373 | 0.160 | 0.279 | 0 | GEÇTİ | 0 / 0 |
| alpha3-002/pickup-1 | 4 | 0.303 | 0.079 | 0.270 | 20 | GEÇTİ | 0 / 1 |
| alpha3-002-repeat/pickup-1 | 4 | 0.295 | 0.135 | 0.259 | 0 | GEÇTİ | 0 / 0 |
| alpha3-002-repeat/pickup-2 | 6 | 2.870 | 0.133 | 3.039 | 21 | GEÇTİ | 0 / 1 |
| alpha3-002-repeat/pickup-3 | 6 | 2.785 | 0.152 | 2.727 | 21 | GEÇTİ | 0 / 0 |
| alpha4-0002/pickup-1 | 4 | 0.317 | 0.171 | 0.298 | 0 | GEÇTİ | 0 / 1 |
| alpha4-0002-repeat/pickup-1 | 4 | 0.230 | 0.115 | 0.320 | 0 | GEÇTİ | 0 / 0 |
| alpha4-0002-repeat/pickup-2 | 4 | 0.340 | 0.125 | 0.279 | 0 | GEÇTİ | 0 / 0 |
| alpha4-0002-repeat/pickup-3 | 4 | 0.341 | 0.179 | 0.292 | 0 | GEÇTİ | 0 / 0 |
| b-landmark/pickup-1 | 4 | 0.382 | 0.229 | 0.285 | 0 | GEÇTİ | 0 / 0 |
| b-landmark/pickup-2 | 4 | 0.324 | 0.231 | 0.313 | 0 | GEÇTİ | 0 / 0 |
| b-landmark/pickup-3 | 4 | 0.505 | 0.327 | 0.268 | 0 | GEÇTİ | 0 / 0 |
| beam-heading0/pickup-1 | 4 | 0.216 | 0.141 | 0.233 | 0 | GEÇTİ | 0 / 0 |
| beam-heading0/pickup-2 | 4 | 0.246 | 0.079 | 0.237 | 0 | GEÇTİ | 0 / 0 |
| beam-heading0/pickup-3 | 4 | 0.216 | 0.059 | 0.233 | 0 | GEÇTİ | 0 / 0 |
| beam-headingpi/pickup-1 | 4 | 0.244 | 0.029 | 0.277 | 0 | GEÇTİ | 0 / 0 |
| beam-headingpi/pickup-2 | 4 | 0.179 | 0.045 | 0.236 | 0 | GEÇTİ | 0 / 0 |
| beam-headingpi/pickup-3 | 4 | 0.235 | 0.101 | 0.242 | 0 | GEÇTİ | 0 / 0 |
| beam-model/pickup-1 | 4 | 0.223 | 0.032 | 0.242 | 0 | GEÇTİ | 0 / 0 |
| beam-model/pickup-2 | 4 | 0.244 | 0.157 | 0.216 | 0 | GEÇTİ | 0 / 0 |
| beam-model/pickup-3 | 4 | 0.154 | 0.019 | 0.233 | 0 | GEÇTİ | 0 / 0 |
| beams180/pickup-1 | 4 | 0.333 | 0.165 | 0.306 | 0 | GEÇTİ | 0 / 0 |
| beams180/pickup-2 | 6 | 2.791 | 0.124 | 2.867 | 21 | GEÇTİ | 0 / 0 |
| beams180/pickup-3 | 4 | 0.317 | 0.140 | 0.284 | 0 | GEÇTİ | 0 / 0 |
| c-heading0/pickup-1 | 4 | 0.288 | 0.105 | 0.338 | 0 | GEÇTİ | 0 / 0 |
| c-heading0/pickup-2 | 4 | 0.369 | 0.249 | 0.289 | 0 | GEÇTİ | 0 / 0 |
| c-heading0/pickup-3 | 4 | 0.426 | 0.342 | 0.278 | 0 | GEÇTİ | 0 / 0 |
| c-headingpi/pickup-1 | 4 | 0.377 | 0.201 | 0.307 | 0 | GEÇTİ | 0 / 0 |
| c-headingpi/pickup-2 | 4 | 0.319 | 0.074 | 0.332 | 0 | GEÇTİ | 0 / 0 |
| c-headingpi/pickup-3 | 4 | 0.368 | 0.137 | 0.291 | 0 | GEÇTİ | 0 / 0 |
| field-prob/pickup-1 | 4 | 0.299 | 0.178 | 0.237 | 0 | GEÇTİ | 0 / 0 |
| field-prob/pickup-2 | 4 | 0.335 | 0.162 | 0.236 | 0 | GEÇTİ | 0 / 0 |
| field-prob/pickup-3 | 4 | 0.363 | 0.201 | 0.230 | 0 | GEÇTİ | 0 / 0 |
| sigma-005/pickup-1 | 6 | 2.966 | 0.146 | 2.912 | 21 | GEÇTİ | 0 / 0 |
| sigma-005/pickup-2 | 6 | 2.866 | 0.165 | 3.124 | 21 | GEÇTİ | 0 / 0 |
| sigma-005/pickup-3 | 6 | 2.969 | 0.162 | 2.999 | 21 | GEÇTİ | 0 / 0 |
| sigma-010/pickup-1 | 6 | 2.982 | 0.147 | 3.103 | 21 | GEÇTİ | 0 / 0 |
| sigma-010/pickup-2 | 6 | 2.878 | 0.167 | 3.035 | 21 | GEÇTİ | 0 / 0 |
| sigma-010/pickup-3 | 6 | 2.906 | — | — | — | DOĞRULANAMADI | 1 / 0 |
| sigma-010-replacement/pickup-1 | 6 | 2.845 | 0.131 | 3.023 | 21 | GEÇTİ | 0 / 0 |
