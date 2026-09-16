"""CPU arithmetic companions to the CUDA textbook; Python standard library only.

Run: python basics.py
These small examples check the mathematics, not CUDA or MPI execution.
"""
from math import atan, cos, floor, isclose, log, pi, sin, sqrt, tanh, cosh


def close(actual, expected):
    assert isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected)


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def pic_step():
    """Trace chapter 10's four-particle example, in normalized units.

    Direct DFT is deliberately for four nodes, not a production FFT substitute.
    The even-grid Nyquist derivative and mean field are set to zero, as in pic1d.py.
    """
    length, cells, dt = 4.0, 4, 0.1
    x = [0.25, 1.25, 2.0, 3.0]
    dx, charge = length/cells, -length/len(x)

    def deposit(positions):
        rho = [1.0] * cells  # immobile ion background
        for position in positions:
            g = (position % length)/dx
            left = floor(g)
            fraction = g-left
            rho[left] += charge*(1-fraction)/dx
            rho[(left+1) % cells] += charge*fraction/dx
        return rho

    def field(rho):
        result = [0j] * cells
        for mode in range(1, cells):
            if 2*mode == cells:
                continue  # Nyquist mode: same convention as the textbook solver
            signed_mode = mode if mode < cells/2 else mode-cells
            k = 2*pi*signed_mode/length
            coefficient = sum(value*complex(cos(k*j*dx), -sin(k*j*dx))
                              for j, value in enumerate(rho))/cells
            electric_coefficient = coefficient/(1j*k)
            for j in range(cells):
                result[j] += electric_coefficient*complex(cos(k*j*dx), sin(k*j*dx))
        for value in result:
            close(value.imag, 0)
        return [value.real for value in result]

    rho = deposit(x)
    electric = field(rho)
    at_particle = []
    for position in x:
        g = (position % length)/dx
        left = floor(g)
        fraction = g-left
        at_particle.append((1-fraction)*electric[left] + fraction*electric[(left+1) % cells])
    acceleration = [-value for value in at_particle]  # electron q/m=-1
    v_minus_half = [-0.5*dt*a for a in acceleration]  # v at integer time 0 is zero
    v_plus_half = [v + dt*a for v, a in zip(v_minus_half, acceleration)]
    new_x = [(position + dt*v) % length for position, v in zip(x, v_plus_half)]
    new_rho = deposit(new_x)
    new_electric = field(new_rho)

    for actual, expected in zip(rho, [0.25, 0, -0.25, 0]):
        close(actual, expected)
    for actual, expected in zip(electric, [0, 1/(2*pi), 0, -1/(2*pi)]):
        close(actual, expected)
    for actual, expected in zip(at_particle, [1/(8*pi), 3/(8*pi), 0, -1/(2*pi)]):
        close(actual, expected)
    expected_x = [0.25-dt*dt/(16*pi), 1.25-3*dt*dt/(16*pi), 2, 3+dt*dt/(4*pi)]
    for actual, expected in zip(new_x, expected_x):
        close(actual, expected)
    close(sum(new_rho)*dx, 0)
    close(sum(new_electric), 0)
    assert any(abs(a-b) > 1e-6 for a, b in zip(electric, new_electric))
    for name, values in [('rho^0', rho), ('E_grid^0', electric), ('E_particle^0', at_particle),
                         ('v^(-1/2)', v_minus_half), ('v^(1/2)', v_plus_half),
                         ('x^1', new_x), ('rho^1', new_rho), ('E_grid^1', new_electric)]:
        print('Ch 10:', name, '=', ', '.join(f'{v:.6f}' for v in values))
    print('Ch 10: one complete electrostatic PIC step PASS (four nodes only)')
    return new_x, new_rho, new_electric


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
    pic_step()

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
