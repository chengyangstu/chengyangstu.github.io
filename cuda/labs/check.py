"""Run all available CPU lab checks with Python + NumPy. Does not validate CUDA/MPI."""
from pathlib import Path
import subprocess
import sys
import tempfile
import numpy as np
from pic1d import check, run

check()
for case in ('landau', 'twostream'):
    data = run(case=case, cells=32, ppc=32, steps=30)
    assert np.isfinite(data).all() and np.max(abs(data[:, 7])) < 1e-12
with tempfile.TemporaryDirectory(prefix='cuda-book-check-') as folder:
    root = Path(folder).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith('cuda-book-check-')
    t = np.linspace(0, 10, 101)
    csv = root / 'known-growth.csv'
    np.savetxt(csv, np.column_stack((t, np.exp(0.3*t))), delimiter=',', header='time,E1_amplitude', comments='')
    analysis = Path(__file__).with_name('analyze.py')
    result = subprocess.run([sys.executable, str(analysis), str(csv), '--start', '2', '--end', '8'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    gamma = float(result.stdout.split('gamma_amplitude=')[1].split(',')[0])
    assert abs(gamma - 0.3) < 1e-7
    invalid = subprocess.run([sys.executable, str(analysis), str(csv), '--start', '8', '--end', '2'], capture_output=True)
    assert invalid.returncode != 0
print('PASS: both warm-plasma initializers, known growth-rate fit and invalid-window rejection. CUDA/MPI not executed.')
