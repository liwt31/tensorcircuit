import pytest
from pytest_lazyfixture import lazy_fixture as lf
import numpy as np

import tensorcircuit as tc
from tensorcircuit.noisemodel import (
    NoiseConf,
    circuit_with_noise,
    expectation_ps_noisfy,
    sample_expectation_ps_noisfy,
)


@pytest.mark.parametrize("backend", [lf("npb"), lf("tfb"), lf("jaxb")])
def test_noisemodel(backend):

    # test data structure
    # noise_conf = NoiseConf()
    # noise_conf.add_noise("h1","t0")
    # noise_conf.add_noise("h1",["t1","t2"],[[0],[1]])
    # noise_conf.add_noise("h1",["t3"],[[0]])
    # noise_conf.add_noise("h2",["v1","v2"],[[0],[1]])
    # noise_conf.add_noise("h2",["v3"],[[0]])

    c = tc.Circuit(2)
    c.cnot(0, 1)
    c.rx(0, theta=0.4)
    c.rx(1, theta=0.8)
    c.h(0)
    c.h(1)

    dmc = tc.DMCircuit(2)
    dmc.cnot(0, 1)
    dmc.rx(0, theta=0.4)
    dmc.rx(1, theta=0.8)
    dmc.h(0)
    dmc.h(1)

    error1 = tc.channels.generaldepolarizingchannel(0.1, 1)
    error2 = tc.channels.generaldepolarizingchannel(0.01, 2)
    error3 = tc.channels.thermalrelaxationchannel(300, 400, 100, "ByChoi", 0)

    readout_error = []
    readout_error.append([0.9, 0.75])  # readout error of qubit 0
    readout_error.append([0.4, 0.7])  # readout error of qubit 1

    noise_conf = NoiseConf()
    noise_conf.add_noise("rx", error1)
    noise_conf.add_noise("rx", [error3], [[0]])
    noise_conf.add_noise("h", [error3, error1], [[0], [1]])
    noise_conf.add_noise("x", [error3], [[0]])
    noise_conf.add_noise("cnot", [error2], [[0, 1]])
    noise_conf.add_noise("readout", readout_error)

    cnoise = circuit_with_noise(c, noise_conf, [0.1] * 7)
    value = cnoise.expectation_ps(x=[0, 1])

    value = expectation_ps_noisfy(c, x=[0, 1], noise_conf=noise_conf, nmc=10000)
    np.testing.assert_allclose(value, 0.15, atol=1e-1)

    value = expectation_ps_noisfy(dmc, x=[0, 1], noise_conf=noise_conf)
    np.testing.assert_allclose(value, 0.15, atol=1e-2)

    # with readout_error
    value = sample_expectation_ps_noisfy(dmc, x=[0, 1], noise_conf=noise_conf)
    np.testing.assert_allclose(value, -0.16, atol=1e-2)

    value = sample_expectation_ps_noisfy(c, x=[0, 1], noise_conf=noise_conf, nmc=100000)
    np.testing.assert_allclose(value, -0.16, atol=1e-1)
