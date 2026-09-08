"""Periodic 1D1V electrostatic electron PIC; immobile uniform ions, normalized units.

Requires NumPy. python pic1d.py --check or python pic1d.py --case cold --output cold.csv
This educational reference does not simulate magnetic reconnection.
"""
import argparse
import csv
from pathlib import Path
import numpy as np


def deposit(x, cells, length):
    g = np.remainder(x, length) * cells / length
    j = np.floor(g).astype(np.int64)
    f = g - j
    # Macro electron charge Q=-L/N; rho has units Q/dx; ions have density +1.
    rho = np.ones(cells)
    np.add.at(rho, j % cells, -(cells / x.size) * (1 - f))
    np.add.at(rho, (j + 1) % cells, -(cells / x.size) * f)
    return rho


def field(rho, length):
    # ik E_k = rho_k. k=0 is neutralized; an even-grid Nyquist derivative is undefined here.
    k = 2 * np.pi * np.fft.rfftfreq(rho.size, d=length / rho.size)
    rh = np.fft.rfft(rho - rho.mean())
    eh = np.zeros_like(rh)
    eh[1:] = rh[1:] / (1j * k[1:])
    if rho.size % 2 == 0:
        eh[-1] = 0
    return np.fft.irfft(eh, n=rho.size)


def gather(x, e, length):
    g = np.remainder(x, length) * e.size / length
    j = np.floor(g).astype(np.int64)
    f = g - j
    return (1 - f) * e[j % e.size] + f * e[(j + 1) % e.size]


def run(case='cold', cells=64, ppc=128, steps=800, dt=0.05, seed=7):
    if cells < 8 or ppc < 2 or steps < 1 or not np.isfinite(dt) or dt <= 0:
        raise ValueError('Require cells>=8, ppc>=2, steps>=1 and dt>0')
    length = 4 * np.pi
    n = cells * ppc
    x0 = (np.arange(n) + 0.5) * length / n
    rng = np.random.default_rng(seed)
    if case == 'cold':
        x = np.remainder(x0 + 0.01 * np.sin(0.5 * x0), length)
        v = np.zeros(n)
    elif case == 'landau':
        # Small density perturbation, v_th=1, k=0.5; statistical convergence is required.
        x = np.remainder(x0 - 0.01 / 0.5 * np.sin(0.5 * x0), length)
        v = rng.normal(size=n)
    elif case == 'twostream':
        x = np.remainder(x0 + 0.01 * np.sin(0.5 * x0), length)
        v = np.where(np.arange(n) % 2, 1.0, -1.0) + 0.1 * rng.normal(size=n)
    else:
        raise ValueError('Unknown case')
    rho = deposit(x, cells, length)
    e = field(rho, length)
    acceleration = -gather(x, e, length)  # electron q/m=-1
    vh = v - 0.5 * dt * acceleration  # store v^{-1/2}
    records = []
    for step in range(steps + 1):
        acceleration = -gather(x, e, length)
        centered_v = vh + 0.5 * dt * acceleration
        kinetic = 0.5 * length / n * np.sum(centered_v**2)
        electric = 0.5 * length / cells * np.sum(e**2)
        mode = np.fft.rfft(e)[1] / cells
        records.append((step * dt, kinetic, electric, kinetic + electric,
                        2 * abs(mode), mode.real, mode.imag, rho.mean()))
        if step == steps:
            break
        vh += dt * acceleration
        x = np.remainder(x + dt * vh, length)
        rho = deposit(x, cells, length)
        e = field(rho, length)
    return np.array(records)


def check():
    for bad_dt in (0, -1, float('nan'), float('inf')):
        try:
            run(dt=bad_dt)
            raise AssertionError('Invalid timestep accepted')
        except ValueError:
            pass
    # Boundary wrapping and shape-function partition of unity.
    x = np.array([-0.1, 0., 0.5, 1., 1.1])
    assert abs(deposit(x, 16, 1.).sum()) < 1e-12
    assert np.max(abs(gather(x, np.ones(16), 1.) - 1)) < 1e-14
    # Analytic periodic Poisson mode: rho=sin(x), E=-cos(x).
    grid = np.arange(64) * 2 * np.pi / 64
    assert np.max(abs(field(np.sin(grid), 2 * np.pi) + np.cos(grid))) < 1e-12
    cold = run(steps=400)
    omega = 2 * np.pi * np.fft.rfftfreq(len(cold), d=0.05)[1:][np.argmax(abs(np.fft.rfft(cold[:, 5]))[1:])]
    assert abs(omega - 1) < 0.12  # finite observation-window frequency resolution
    drift = np.max(abs(cold[:, 3] - cold[0, 3])) / cold[0, 3]
    assert drift < 0.03 and np.max(abs(cold[:, 7])) < 1e-12
    print(f'PASS: CIC, periodic Poisson, cold plasma omega={omega:.4f}, relative energy drift={drift:.3g}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--case', choices=['cold', 'landau', 'twostream'], default='cold')
    parser.add_argument('--cells', type=int, default=64)
    parser.add_argument('--ppc', type=int, default=128)
    parser.add_argument('--steps', type=int, default=800)
    parser.add_argument('--dt', type=float, default=0.05)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--output', type=Path, default=Path('pic.csv'))
    args = parser.parse_args()
    if args.check:
        check()
    else:
        history = run(args.case, args.cells, args.ppc, args.steps, args.dt, args.seed)
        with args.output.open('x', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            writer.writerow(('time','kinetic','electric','total','E1_amplitude','E1_real','E1_imag','mean_charge'))
            writer.writerows(history)
        print('Wrote', args.output)
