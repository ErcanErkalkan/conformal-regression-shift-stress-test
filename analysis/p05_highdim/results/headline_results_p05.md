# P0-5 headline results

- Final design: nested nuisance-coordinate stress with p={5,20,50,100}; predictor fixed to first five signal coordinates; full p used only by density-ratio/oracle weighting.
- 30 paired repetitions; four analytic shift families; severity anchors {0,1,2}; 4,320 frozen method-condition rows.
- All 1,080 unique estimated-ratio fits converged.

- mean: Estimated-WCP p100-p5 A_cov = 0.1741 (95% CI 0.1203, 0.2278); Oracle-WCP = 0.0015 (-0.0038, 0.0068).
- mixture: Estimated-WCP p100-p5 A_cov = 0.2329 (95% CI 0.1777, 0.2881); Oracle-WCP = -0.0043 (-0.0123, 0.0038).
- tail_mixture: Estimated-WCP p100-p5 A_cov = 0.1107 (95% CI 0.0756, 0.1457); Oracle-WCP = -0.0065 (-0.0135, 0.0005).
- variance: Estimated-WCP p100-p5 A_cov = 0.0333 (95% CI 0.0110, 0.0555); Oracle-WCP = -0.0002 (-0.0188, 0.0183).

- Zero-shift p=100 negative control: held-out domain AUC 0.4982, Estimated-WCP coverage 0.8373, calibration ESS ratio 0.00843, analytic log-weight RMSE 5.6609.
- Variance shift p=100, delta=2: Oracle-WCP coverage 0.99992 with unbounded-interval fraction 0.99984.
- Tail-mixture p=100, delta=2: oracle calibration ESS ratio approximately 1.0 while unbounded-interval fraction is 0.29983.
- Degree-2 expansion grows from 20 features at p=5 to 5,150 at p=100; mean ratio-fit time grows from about 0.011 s to 0.971 s per condition in this audit environment.
