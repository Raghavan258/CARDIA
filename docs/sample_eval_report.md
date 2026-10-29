# CARDIA Evaluation Report

Generated: `2026-10-29T07:54:28.907646+00:00`

Not a medical device. Metrics are for engineering evaluation only.

## Dataset

- **type**: synthetic
- **reference_bpm**: 72.0
- **duration_s**: 6.0
- **motion_at_s**: 5.0
- **split**: evaluation
- **limitation**: Synthetic RGB/landmark sequence — not a clinical dataset. Do not treat MAE on this fixture as real-world accuracy.

## Baseline (quality gating off)

| Metric | Value |
|---|---|
| `name` | synthetic_72bpm |
| `mode` | synthetic |
| `algorithm` | pos |
| `gating_enabled` | False |
| `duration_s` | 5.966666666666667 |
| `frame_count` | 180 |
| `processing_fps` | 83.50526138820847 |
| `mean_latency_ms` | 11.962339444370526 |
| `face_track_fraction` | 1.0 |
| `valid_estimate_coverage` | 0.65 |
| `rejection_rate` | 0.4 |
| `hr_mae` | 0.6055452965484878 |
| `hr_rmse` | 1.2562420398087148 |
| `hr_bias` | 0.5783215330346361 |
| `paired_reference_count` | 117 |
| quality_fraction.initializing | 0.35 |
| quality_fraction.good | 0.6 |
| quality_fraction.fair | 0.0 |
| quality_fraction.poor | 0.05 |
| rejection.INSUFFICIENT_SIGNAL_DURATION | 63 |
| rejection.ABRUPT_LANDMARK_DISPLACEMENT | 2 |
| rejection.EXCESSIVE_MOTION | 9 |

## Improved (quality gating on)

| Metric | Value |
|---|---|
| `name` | synthetic_72bpm |
| `mode` | synthetic |
| `algorithm` | pos |
| `gating_enabled` | True |
| `duration_s` | 5.966666666666667 |
| `frame_count` | 180 |
| `processing_fps` | 117.2706888948175 |
| `mean_latency_ms` | 8.515356666642523 |
| `face_track_fraction` | 1.0 |
| `valid_estimate_coverage` | 0.4777777777777778 |
| `rejection_rate` | 0.5222222222222223 |
| `hr_mae` | 0.8238232522809901 |
| `hr_rmse` | 1.4652678750340429 |
| `hr_bias` | 0.7867862716865639 |
| `paired_reference_count` | 86 |
| quality_fraction.initializing | 0.5166666666666667 |
| quality_fraction.good | 0.4777777777777778 |
| quality_fraction.fair | 0.0 |
| quality_fraction.poor | 0.005555555555555556 |
| rejection.INSUFFICIENT_SIGNAL_DURATION | 93 |
| rejection.ABRUPT_LANDMARK_DISPLACEMENT | 2 |
| rejection.EXCESSIVE_MOTION | 2 |

## Delta (gated − baseline)

- **valid_estimate_coverage**: -0.17222222222222222
- **rejection_rate**: 0.12222222222222223
- **processing_fps**: 33.76542750660903
- **hr_mae**: 0.2182779557325023
- **hr_rmse**: 0.20902583522532803

## Notes

