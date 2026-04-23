from agent.calibration import PlattScaler, fit_regime_calibrator


def test_platt_scaler_predict_bounds():
    scaler = PlattScaler(slope=1.2, intercept=-0.1)
    calibrated = scaler.predict(0.67)
    assert 0.0 < calibrated < 1.0


def test_fit_regime_calibrator_fits_when_data_is_sufficient():
    labels = ["LOW_VOL"] * 12 + ["MID_VOL"] * 12 + ["HIGH_VOL"] * 12
    probs = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.55, 0.60, 0.65, 0.70, 0.75] * 3
    outcomes = [0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1] * 3

    calibrator = fit_regime_calibrator(labels, probs, outcomes)

    low = calibrator.calibrate("LOW_VOL", 0.65)
    mid = calibrator.calibrate("MID_VOL", 0.65)
    high = calibrator.calibrate("HIGH_VOL", 0.65)

    assert 0.0 < low < 1.0
    assert 0.0 < mid < 1.0
    assert 0.0 < high < 1.0
