import pytest
import numpy as np
from scipy import optimize, signal

from alphacsc.update_d_multi import _gradient_d, _gradient_uv, _get_D
from alphacsc.update_d_multi import _shifted_objective_uv
from alphacsc.update_d_multi import update_uv, prox_uv, _get_d_update_constants
from alphacsc.utils import construct_X_multi


DEBUG = False


def test_simple():
    T = 100
    L = 10
    S = T - L + 1
    x = np.random.random(T)
    z = np.random.random(S)
    d = np.random.random(L)

    def func(d0):
        xr = signal.convolve(z, d0)
        residual = x - xr
        return .5 * np.sum(residual * residual)

    def grad(d0):
        xr = signal.convolve(z, d0)
        residual = x - xr
        grad_d = - signal.convolve(residual, z[::-1], mode='valid')
        return grad_d

    error = optimize.check_grad(func, grad, d, epsilon=1e-8)
    assert error < 1e-4, "Gradient is false: {:.4e}".format(error)

# def test_simple2():
#     L = 35000
#     d = np.random.random(L)

#     def func(d0):
#         return d0.dot(d0)

#     def grad(d0):
#         return 2 * d0

#     error = optimize.check_grad(func, grad, d, epsilon=1e-8)
#     assert error < 1e-4, f"Gradient is false: {error:.4e}"


def test_gradient_d():
    # Generate synchronous D
    n_times_atom, n_times = 10, 100
    n_chan = 5
    n_atoms = 2
    n_trials = 3

    rng = np.random.RandomState()
    X = rng.normal(size=(n_trials, n_chan, n_times))
    Z = rng.normal(size=(n_atoms, n_trials, n_times - n_times_atom + 1))
    D = rng.normal(size=(n_atoms, n_chan, n_times_atom))

    def func(d0):
        D0 = d0.reshape(n_atoms, n_chan, n_times_atom)
        X_hat = construct_X_multi(Z, D0)
        res = X - X_hat
        return .5 * np.sum(res * res)

    def grad(d0):
        D0 = d0.reshape(n_atoms, n_chan, n_times_atom)
        return _gradient_d(D0, X, Z).ravel()

    if DEBUG:
        grad_approx = optimize.approx_fprime(D.ravel(), func, 2e-8)
        grad_d = grad(D.ravel())

        import matplotlib.pyplot as plt
        plt.semilogy(abs(grad_approx - grad_d))
        plt.figure()
        plt.plot(grad_approx, label="approx")
        plt.plot(grad_d, '--', label="grad")
        plt.legend()
        plt.show()

    error = optimize.check_grad(func, grad, D.ravel(), epsilon=2e-8)
    assert error < 1e-3, "Gradient is false: {:.4e}".format(error)


def test_gradient_uv():
    # Generate synchronous D
    n_times_atom, n_times = 10, 100
    n_chan = 5
    n_atoms = 2
    n_trials = 3

    rng = np.random.RandomState()
    X = rng.normal(size=(n_trials, n_chan, n_times))
    Z = rng.normal(size=(n_atoms, n_trials, n_times - n_times_atom + 1))
    uv = rng.normal(size=(n_atoms, n_chan + n_times_atom))

    def func(uv0):
        uv0 = uv0.reshape(n_atoms, n_chan + n_times_atom)
        D0 = _get_D(uv0, n_chan)
        X_hat = construct_X_multi(Z, D0)
        res = X - X_hat
        return .5 * np.sum(res * res)

    def grad(uv0):
        uv0 = uv0.reshape(n_atoms, n_chan + n_times_atom)
        return _gradient_uv(uv0, X, Z).ravel()

    if DEBUG:
        grad_approx = optimize.approx_fprime(uv.ravel(), func, 2e-8)
        grad_d = grad(uv.ravel())

        import matplotlib.pyplot as plt
        plt.semilogy(abs(grad_approx - grad_d))
        plt.figure()
        plt.plot(grad_approx, label="approx")
        plt.plot(grad_d, '--', label="grad")
        plt.legend()
        plt.show()

    error = optimize.check_grad(func, grad, uv.ravel(), epsilon=2e-8)
    assert error < 1e-3, "Gradient is false: {:.4e}".format(error)

    constants = _get_d_update_constants(X, Z)
    msg = "Wrong value for Zt*X"
    assert np.allclose(_gradient_uv(0 * uv, X, Z),
                       _gradient_uv(0 * uv, constants=constants)), msg
    msg = "Wrong value for Zt*Z"
    assert np.allclose(_gradient_uv(uv, X, Z),
                       _gradient_uv(uv, constants=constants)), msg


@pytest.mark.parametrize('uv_constraint', ['separate'])
def test_update_uv(uv_constraint):
    # Generate synchronous D
    n_times_atom, n_times = 10, 100
    n_chan = 5
    n_atoms = 2
    n_trials = 3

    rng = np.random.RandomState()
    Z = rng.normal(size=(n_atoms, n_trials, n_times - n_times_atom + 1))
    uv0 = rng.normal(size=(n_atoms, n_chan + n_times_atom))
    uv1 = rng.normal(size=(n_atoms, n_chan + n_times_atom))

    uv0 = prox_uv(uv0)
    uv1 = prox_uv(uv1)

    D0 = _get_D(uv0, n_chan)
    X = construct_X_multi(Z, D0)

    def objective(uv):
        D = _get_D(uv, n_chan)
        X_hat = construct_X_multi(Z, D)
        res = X - X_hat
        return .5 * np.sum(res * res)

    # Ensure that the known optimal point is stable
    uv = update_uv(X, Z, uv0, max_iter=1000, verbose=0,
                   uv_constraint=uv_constraint)
    cost = objective(uv)

    assert np.isclose(cost, 0), "optimal point not stable"
    assert np.allclose(uv, uv0), "optimal point not stable"

    # Ensure that the update is going down from a random initialization
    cost0 = objective(uv1)
    uv, pobj = update_uv(X, Z, uv1, debug=True, max_iter=5000, verbose=10,
                         momentum=False, eps=1e-15,
                         uv_constraint=uv_constraint)
    cost1 = objective(uv)

    if False:
        import matplotlib.pyplot as plt
        pobj = np.array(pobj)
        plt.semilogy(pobj - np.min(pobj) + 1e-26)
        plt.show()

    try:
        assert cost1 < cost0, "Learning is not going down"

        assert np.isclose(cost1, 0)
    except AssertionError:

        import matplotlib.pyplot as plt
        pobj = np.array(pobj)
        plt.semilogy(pobj)
        plt.show()
        raise


def test_fast_cost():
    """Test that _shifted_objective_uv compute the right thing"""
    # Generate synchronous D
    n_times_atom, n_times = 10, 100
    n_chan = 5
    n_atoms = 2
    n_trials = 3

    rng = np.random.RandomState()
    X = rng.normal(size=(n_trials, n_chan, n_times))
    Z = rng.normal(size=(n_atoms, n_trials, n_times - n_times_atom + 1))

    constants = _get_d_update_constants(X, Z)

    def objective(uv):
        D = _get_D(uv, n_chan)
        X_hat = construct_X_multi(Z, D)
        res = X - X_hat
        return .5 * np.sum(res * res)

    for _ in range(10):
        uv = rng.normal(size=(n_atoms, n_chan + n_times_atom))

        nX = np.sum(X * X)
        cost_fast = _shifted_objective_uv(uv, constants) + .5 * nX
        cost_full = objective(uv)
        assert np.isclose(cost_full, cost_fast)
