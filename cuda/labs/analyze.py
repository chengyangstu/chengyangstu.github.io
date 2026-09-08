"""Fit an explicitly chosen exponential interval, never auto-select a flattering window.
python analyze.py cold.csv --start 2 --end 8
For oscillatory Landau damping, first select envelope peaks; raw amplitude contains zeros.
"""
import argparse
import numpy as np

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv')
    p.add_argument('--start', type=float, required=True)
    p.add_argument('--end', type=float, required=True)
    p.add_argument('--peaks', action='store_true', help='fit local envelope maxima only')
    a = p.parse_args()
    data = np.genfromtxt(a.csv, delimiter=',', names=True)
    t, y = data['time'], data['E1_amplitude']
    keep = (t >= a.start) & (t <= a.end) & (y > 0) & np.isfinite(y)
    if a.peaks:
        peaks = np.zeros(len(y), dtype=bool)
        peaks[1:-1] = (y[1:-1] > y[:-2]) & (y[1:-1] >= y[2:])
        keep &= peaks
    if a.end <= a.start or keep.sum() < 3:
        p.error('Select at least three finite samples or envelope peaks in a nonempty interval')
    slope, intercept = np.polyfit(t[keep], np.log(y[keep]), 1)
    residual = np.sqrt(np.mean((np.log(y[keep]) - (slope*t[keep] + intercept))**2))
    print(f'gamma_amplitude={slope:.8g}, log_residual_RMS={residual:.4g}, samples={keep.sum()}')
    print('A fit is not proof of a linear regime. Compare windows, resolutions and independent seeds.')
