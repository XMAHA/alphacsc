import numpy as np

from numpy.testing import assert_allclose, assert_raises

from alphacsc.utils.lil import convert_to_list_of_lil
from alphacsc.utils.lil import convert_from_list_of_lil
from alphacsc.utils.lil import safe_sum, get_Z_shape, scale_Z_by_atom
from alphacsc.utils.lil import is_list_of_lil, is_lil


def test_is_list_of_lil():
    n_atoms, n_trials, n_times_valid = 3, 2, 10
    Z = np.random.randn(n_atoms, n_trials, n_times_valid)
    Z_lil = convert_to_list_of_lil(Z)

    assert is_list_of_lil(Z_lil)
    assert not is_list_of_lil(Z)
    assert_raises(TypeError, is_list_of_lil, Z_lil[0])
    assert_raises(TypeError, is_list_of_lil, Z[0])

    assert is_lil(Z_lil[0])
    assert not is_lil(Z[0])
    assert_raises(TypeError, is_lil, Z_lil)
    assert_raises(TypeError, is_lil, Z)


def test_get_Z_shape():
    n_atoms, n_trials, n_times_valid = 3, 2, 10
    Z = np.random.randn(n_atoms, n_trials, n_times_valid)
    Z_lil = convert_to_list_of_lil(Z)
    assert_allclose(get_Z_shape(Z), get_Z_shape(Z_lil))


def test_safe_sum():
    n_atoms, n_trials, n_times_valid = 3, 2, 10
    Z = np.random.randn(n_atoms, n_trials, n_times_valid)
    Z_lil = convert_to_list_of_lil(Z)
    for axis in [None, (1, 2)]:
        assert_allclose(safe_sum(Z, axis), safe_sum(Z_lil, axis))


def test_conversion():
    n_atoms, n_trials, n_times_valid = 3, 2, 10
    Z = np.random.randn(n_atoms, n_trials, n_times_valid)
    Z_lil = convert_to_list_of_lil(Z)
    Z_2 = convert_from_list_of_lil(Z_lil)
    assert_allclose(Z, Z_2)


def test_scale_Z_by_atom():
    n_atoms, n_trials, n_times_valid = 3, 2, 10
    scale = np.random.randn(n_atoms)
    Z = np.random.randn(n_atoms, n_trials, n_times_valid)
    Z_lil = convert_to_list_of_lil(Z)
    Z_scaled = scale_Z_by_atom(Z, scale)
    Z_lil_scaled = scale_Z_by_atom(Z_lil, scale)
    assert_allclose(Z_scaled, convert_from_list_of_lil(Z_lil_scaled))
