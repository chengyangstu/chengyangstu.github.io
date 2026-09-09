"""CPU arithmetic companions to the CUDA textbook; Python standard library only.

Run: python basics.py
These small examples check the mathematics, not CUDA or MPI execution.
"""
from math import atan, isclose, log, pi, sin, sqrt, tanh, cosh


def close(actual, expected):
    assert isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected)


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def main():
    # Chapters 1, 4, 5: an update, an error norm, and complete thread coverage.
    close(0.2 + 3*0.1, 0.5)
    actual = [x + 0.1*v for x, v in zip([0, 1, 2], [1, -1, 0])]
    for a, b in zip(actual, [0.1, 0.9, 2]):
        close(a, b)
    close(sqrt((4.1 - 4)**2 / (3**2 + 4**2)), 0.02)
    for n, threads, blocks in [(10, 4, 3), (10, 4, 2), (17, 8, 3), (17, 8, 2)]:
        visits = [0] * n
        for block in range(blocks):
            for thread in range(threads):
                for index in range(block*threads + thread, n, blocks*threads):
                    visits[index] += 1
        assert visits == [1] * n
    print('Ch 1/4/5: positions =', actual, '; relative L2 = 0.02; index coverage PASS')

    # Chapters 9, 10: normalized CIC density and one leapfrog step.
    charge, dx, fraction = -2.0, 0.5, 0.3
    rho_left, rho_right = charge*(1-fraction)/dx, charge*fraction/dx
    close((rho_left + rho_right)*dx, charge)
    field = (1-fraction)*2 + fraction*6
    close(field, 3.2)
    close(-0.2 % 1, 0.8)
    close(2.3 % 1, 0.3)
    x, vh, electric, dt = 0.4, 0.2, 0.5, 0.1
    centered = vh - 0.5*dt*electric
    vh -= dt*electric
    x += dt*vh
    close(centered, 0.175)
    close(vh, 0.15)
    close(x, 0.415)
    print(f'Ch 9/10: CIC = {rho_left:g}, {rho_right:g}; E = {field:g}; new x = {x:g}')

    # Chapter 11: Boris pure magnetic rotation, electron q/m=-1, Bz=1.
    v = (1.0, 0.0, 0.0)
    t = (0.0, 0.0, -0.1)
    s = tuple(2*a/(1+sum(b*b for b in t)) for a in t)
    intermediate = tuple(a+b for a, b in zip(v, cross(v, t)))
    rotated = tuple(a+b for a, b in zip(v, cross(intermediate, s)))
    close(rotated[0], 99/101)
    close(rotated[1], 20/101)
    close(sum(a*a for a in rotated), 1)
    print(f'Ch 11: Boris v = {rotated}; angle = {2*atan(0.1):.9f} rad')

    # Chapters 13, 15, 16: local continuity, exponential rate, Harris pressure.
    delta_rho, dx, dt, current_left = -0.2, 0.5, 0.1, 0.2
    current_right = current_left - dx/dt*delta_rho
    close(current_right, 1.2)
    close(delta_rho/dt + (current_right-current_left)/dx, 0)
    growth = log(0.02/0.01)/5
    close(log((0.02/0.01)**2)/5, 2*growth)
    for y in [-2, -0.5, 0, 0.5, 2]:
        density = 1/cosh(y/0.5)**2
        magnetic = tanh(y/0.5)
        close(density*(0.25+0.25) + magnetic**2/2, 0.5)
        close(density*(1*(-1) + (-1)*1), -2*density)
    print(f'Ch 13/15/16: right current = {current_right:g}; growth = {growth:.6f}; Harris PASS')

    # Chapter 19: two-subdomain stencil agrees with a discrete Fourier mode.
    # CPU emulates owned points and ghosts; this does NOT test MPI communication.
    n, alpha = 8, 0.2
    old = [sin(2*pi*j/n) for j in range(n)]
    factor = 1 - 4*alpha*sin(pi/n)**2
    for step in range(1, 6):
        new = []
        for start in (0, 4):
            local = [old[(start+j) % n] for j in range(-1, 5)]
            new.extend(local[j] + alpha*(local[j-1]-2*local[j]+local[j+1])
                       for j in range(1, 5))
        for j, value in enumerate(new):
            close(value, factor**step*sin(2*pi*j/n))
        old = new
    close(10/(4*3), 5/6)
    print('Ch 19: CPU ghost/stencil arithmetic PASS; strong scaling efficiency = 83.333%')
    print('PASS: textbook arithmetic only; no GPU, MPI, or complete reconnection solver was run.')


if __name__ == '__main__':
    main()
