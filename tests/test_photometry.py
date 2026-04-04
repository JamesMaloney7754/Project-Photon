"""Tests for photon.core.photometry, photon.core.star_detector, and SettingsManager."""

from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gaussian_image(
    shape: tuple[int, int],
    sources: list[tuple[float, float, float]],  # (x, y, amplitude)
    sigma: float = 2.0,
    noise_std: float = 10.0,
    seed: int = 42,
) -> np.ndarray:
    """Return a 2-D array with Gaussian blobs at the given positions."""
    rng = np.random.default_rng(seed)
    h, w = shape
    ys, xs = np.ogrid[:h, :w]
    image = rng.normal(1000.0, noise_std, (h, w))
    for (cx, cy, amp) in sources:
        image += amp * np.exp(-((xs - cx) ** 2 + (ys - cy) ** 2) / (2 * sigma ** 2))
    return image.astype(np.float64)


# ---------------------------------------------------------------------------
# test_detect_stars_returns_table
# ---------------------------------------------------------------------------


def test_detect_stars_returns_table() -> None:
    """detect_stars returns a Table with at least 3 rows and required columns."""
    pytest.importorskip("photutils")

    sources = [
        (30.0, 30.0, 5000.0),
        (50.0, 20.0, 4000.0),
        (15.0, 45.0, 3500.0),
        (55.0, 55.0, 3000.0),
        (10.0, 10.0, 2500.0),
    ]
    image = _make_gaussian_image((80, 80), sources, sigma=2.5, noise_std=5.0)

    from photon.core.star_detector import detect_stars

    stars = detect_stars(image, fwhm=3.0, threshold_sigma=3.0)

    assert len(stars) >= 3, f"Expected ≥3 sources, got {len(stars)}"
    for col in ("xcentroid", "ycentroid", "flux"):
        assert col in stars.colnames, f"Missing column '{col}'"


# ---------------------------------------------------------------------------
# test_select_comparison_excludes_target
# ---------------------------------------------------------------------------


def test_select_comparison_excludes_target() -> None:
    """select_comparison_stars excludes stars near the target position."""
    pytest.importorskip("photutils")

    sources = [
        (32.0, 32.0, 8000.0),  # target
        (50.0, 20.0, 4000.0),
        (15.0, 45.0, 3500.0),
        (60.0, 60.0, 3000.0),
        (10.0, 10.0, 2000.0),
    ]
    image = _make_gaussian_image((80, 80), sources, sigma=2.5, noise_std=5.0)

    from photon.core.star_detector import detect_stars, select_comparison_stars

    stars = detect_stars(image, fwhm=3.0, threshold_sigma=3.0)
    assert len(stars) >= 2

    target_x, target_y = 32.0, 32.0
    comps = select_comparison_stars(
        stars,
        target_x, target_y,
        exclusion_radius_px=15.0,
        min_snr=0.0,   # low threshold so we don't over-filter on synthetic data
    )

    # No comparison should be within 15px of the target
    import numpy as np
    if len(comps) > 0:
        xs = np.asarray(comps["xcentroid"], dtype=float)
        ys = np.asarray(comps["ycentroid"], dtype=float)
        dists = np.sqrt((xs - target_x) ** 2 + (ys - target_y) ** 2)
        assert np.all(dists > 15.0), (
            f"Comparison star too close to target: min dist = {dists.min():.1f} px"
        )


# ---------------------------------------------------------------------------
# test_aperture_photometry_shape
# ---------------------------------------------------------------------------


def test_aperture_photometry_shape() -> None:
    """run_aperture_photometry returns arrays with shape (N_frames,)."""
    pytest.importorskip("photutils")

    n_frames = 3
    image = _make_gaussian_image(
        (100, 100),
        [(50.0, 50.0, 10000.0), (70.0, 30.0, 5000.0)],
        sigma=3.0, noise_std=10.0,
    )
    stack = np.stack([image] * n_frames)

    from photon.core.photometry import run_aperture_photometry

    result = run_aperture_photometry(
        stack,
        target_xy=(50.0, 50.0),
        comparison_xys=[(70.0, 30.0)],
        aperture_radius=6.0,
        annulus_inner=9.0,
        annulus_outer=14.0,
    )

    assert result["target_flux"].shape  == (n_frames,), "target_flux shape mismatch"
    assert result["target_mag"].shape   == (n_frames,), "target_mag shape mismatch"
    assert result["differential_mag"].shape == (n_frames,), "diff_mag shape mismatch"
    assert result["comparison_fluxes"].shape == (n_frames, 1), "comp_fluxes shape mismatch"
    assert np.all(np.isfinite(result["target_flux"])), "target_flux contains non-finite values"
    assert np.all(result["target_flux"] > 0), "target_flux contains non-positive values"


# ---------------------------------------------------------------------------
# test_settings_manager_defaults
# ---------------------------------------------------------------------------


def test_settings_manager_defaults() -> None:
    """SettingsManager.get() returns the correct default for aperture_radius_px."""
    # Reset singleton so we get a fresh instance
    import photon.core.settings_manager as sm_mod
    sm_mod._instance = None

    from photon.core.settings_manager import SettingsManager

    sm = SettingsManager()
    value = sm.get("photometry/aperture_radius_px")
    assert value == pytest.approx(8.0), f"Expected 8.0, got {value!r}"

    # Also verify a string default
    backend = sm.get("platesolve/backend")
    assert backend == "astap", f"Expected 'astap', got {backend!r}"

    # Reset singleton after test
    sm_mod._instance = None


# ---------------------------------------------------------------------------
# test_snap_to_nearest_star
# ---------------------------------------------------------------------------


def test_snap_to_nearest_star_finds_closest() -> None:
    """snap_to_nearest_star returns the index of the closest star."""
    pytest.importorskip("photutils")

    sources = [
        (20.0, 20.0, 5000.0),
        (50.0, 50.0, 4000.0),
        (70.0, 70.0, 3000.0),
    ]
    image = _make_gaussian_image((100, 100), sources, sigma=2.5, noise_std=5.0)

    from photon.core.star_detector import detect_stars, snap_to_nearest_star

    stars = detect_stars(image, fwhm=3.0, threshold_sigma=3.0)
    assert len(stars) >= 2

    # Click very close to one detected star
    xs = list(stars["xcentroid"])
    ys = list(stars["ycentroid"])
    target_row = 0
    click_x = xs[target_row] + 2.0   # 2 px offset
    click_y = ys[target_row] + 2.0

    row = snap_to_nearest_star(click_x, click_y, stars, max_distance_px=10.0)
    assert row == target_row, f"Expected row {target_row}, got {row}"


def test_snap_to_nearest_star_returns_none_when_too_far() -> None:
    """snap_to_nearest_star returns None when no star is within range."""
    pytest.importorskip("photutils")

    sources = [(50.0, 50.0, 5000.0)]
    image = _make_gaussian_image((100, 100), sources, sigma=2.5, noise_std=5.0)

    from photon.core.star_detector import detect_stars, snap_to_nearest_star

    stars = detect_stars(image, fwhm=3.0, threshold_sigma=3.0)

    # Click far from the only star
    row = snap_to_nearest_star(5.0, 5.0, stars, max_distance_px=5.0)
    assert row is None


# ---------------------------------------------------------------------------
# test_build_light_curve
# ---------------------------------------------------------------------------


def test_build_light_curve_columns_and_length() -> None:
    """build_light_curve produces a Table with the expected columns and length."""
    import numpy as np
    from photon.core.photometry import build_light_curve

    n = 10
    diff_mags = np.random.default_rng(0).normal(0.0, 0.005, n)
    table = build_light_curve(diff_mags, observation_times=None)

    assert len(table) == n
    for col in ("time", "mag", "mag_err", "flagged", "frame_index"):
        assert col in table.colnames, f"Missing column '{col}'"
    assert not any(table["flagged"]), "Expected no flagged frames by default"


def test_build_light_curve_respects_frame_flags() -> None:
    """Flagged frames appear in the table with flagged=True."""
    import numpy as np
    from photon.core.photometry import build_light_curve

    n = 5
    diff_mags = np.zeros(n)
    flags = np.array([False, True, False, True, False])
    table = build_light_curve(diff_mags, observation_times=None, frame_flags=flags)

    assert list(table["flagged"]) == [False, True, False, True, False]


# ---------------------------------------------------------------------------
# test_aperture_photometry_out_of_bounds
# ---------------------------------------------------------------------------


def test_aperture_photometry_raises_on_out_of_bounds() -> None:
    """run_aperture_photometry raises PhotometryError for edge-clipping apertures."""
    pytest.importorskip("photutils")

    import numpy as np
    from photon.core.photometry import PhotometryError, run_aperture_photometry

    stack = np.ones((2, 50, 50))

    with pytest.raises(PhotometryError):
        run_aperture_photometry(
            stack,
            target_xy=(2.0, 2.0),   # too close to the edge
            comparison_xys=[(25.0, 25.0)],
            annulus_outer=15.0,
        )
