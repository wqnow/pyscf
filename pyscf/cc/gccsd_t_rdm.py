#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import numpy
from pyscf import lib
from pyscf.lib import logger
from pyscf.cc import gccsd_rdm

def _gamma1_intermediates(mycc, t1, t2, l1, l2, eris=None):
    doo, dov, dvo, dvv = gccsd_rdm._gamma1_intermediates(mycc, t1, t2, l1, l2)

    if eris is None: eris = mycc.ao2mo()

    nocc, nvir = t1.shape
    bcei = numpy.asarray(eris.ovvv).conj().transpose(3,2,1,0)
    majk = numpy.asarray(eris.ooov).conj().transpose(2,3,0,1)
    bcjk = numpy.asarray(eris.oovv).conj().transpose(2,3,0,1)

    mo_e = eris.fock.diagonal().real
    eia = mo_e[:nocc,None] - mo_e[nocc:]
    d3 = lib.direct_sum('ia+jb+kc->ijkabc', eia, eia, eia)

    t3c =(numpy.einsum('jkae,bcei->ijkabc', t2, bcei)
        - numpy.einsum('imbc,majk->ijkabc', t2, majk))
    t3c = t3c - t3c.transpose(0,1,2,4,3,5) - t3c.transpose(0,1,2,5,4,3)
    t3c = t3c - t3c.transpose(1,0,2,3,4,5) - t3c.transpose(2,1,0,3,4,5)
    t3c /= d3

    t3d = numpy.einsum('ia,bcjk->ijkabc', t1, bcjk)
    t3d += numpy.einsum('ai,jkbc->ijkabc', eris.fock[nocc:,:nocc], t2)
    t3d = t3d - t3d.transpose(0,1,2,4,3,5) - t3d.transpose(0,1,2,5,4,3)
    t3d = t3d - t3d.transpose(1,0,2,3,4,5) - t3d.transpose(2,1,0,3,4,5)
    t3d /= d3

    goo = numpy.einsum('iklabc,jklabc->ij', (t3c+t3d).conj(), t3c) * (1./12)
    gvv = numpy.einsum('ijkacd,ijkbcd->ab', t3c+t3d, t3c.conj()) * (1./12)
    doo[numpy.diag_indices(nocc)] -= goo.diagonal()
    dvv[numpy.diag_indices(nvir)] += gvv.diagonal()
    dvo += numpy.einsum('ijab,ijkabc->ck', t2.conj(), t3c) * (1./4)

    return doo, dov, dvo, dvv

# gamma2 intermediates in Chemist's notation
def _gamma2_intermediates(mycc, t1, t2, l1, l2, eris=None):
    dovov, dvvvv, doooo, doovv, dovvo, dvvov, dovvv, dooov = \
            gccsd_rdm._gamma2_intermediates(mycc, t1, t2, l1, l2)
    if eris is None: eris = mycc.ao2mo()

    nocc, nvir = t1.shape
    bcei = numpy.asarray(eris.ovvv).conj().transpose(3,2,1,0)
    majk = numpy.asarray(eris.ooov).conj().transpose(2,3,0,1)
    bcjk = numpy.asarray(eris.oovv).conj().transpose(2,3,0,1)

    mo_e = eris.fock.diagonal().real
    eia = mo_e[:nocc,None] - mo_e[nocc:]
    d3 = lib.direct_sum('ia+jb+kc->ijkabc', eia, eia, eia)

    t3c =(numpy.einsum('jkae,bcei->ijkabc', t2, bcei)
        - numpy.einsum('imbc,majk->ijkabc', t2, majk))
    t3c = t3c - t3c.transpose(0,1,2,4,3,5) - t3c.transpose(0,1,2,5,4,3)
    t3c = t3c - t3c.transpose(1,0,2,3,4,5) - t3c.transpose(2,1,0,3,4,5)
    t3c /= d3

    t3d = numpy.einsum('ia,bcjk->ijkabc', t1, bcjk)
    t3d += numpy.einsum('ai,jkbc->ijkabc', eris.fock[nocc:,:nocc], t2)
    t3d = t3d - t3d.transpose(0,1,2,4,3,5) - t3d.transpose(0,1,2,5,4,3)
    t3d = t3d - t3d.transpose(1,0,2,3,4,5) - t3d.transpose(2,1,0,3,4,5)
    t3d /= d3

    goovv  = numpy.einsum('kc,ijkabc->ijab', t1.conj(), t3c).conj() * (1./4)
    dovov += goovv.transpose(0,2,1,3) - goovv.transpose(0,3,1,2)

    m3 = t3c * 2 + t3d
    gooov  = numpy.einsum('imbc,ijkabc->jkma', t2, m3.conj()) * (1./8)
    dooov -= gooov.transpose(0,2,1,3) - gooov.transpose(1,2,0,3)

    govvv  = numpy.einsum('jkae,ijkabc->iecb', t2, m3.conj()) * (1./8)
    dovvv += govvv.transpose(0,2,1,3) - govvv.transpose(0,3,1,2)
    return dovov, dvvvv, doooo, doovv, dovvo, dvvov, dovvv, dooov

def make_rdm1(mycc, t1, t2, l1, l2, eris=None):
    d1 = _gamma1_intermediates(mycc, t1, t2, l1, l2, eris)
    return gccsd_rdm._make_rdm1(mycc, d1, True)

# rdm2 in Chemist's notation
def make_rdm2(mycc, t1, t2, l1, l2, eris=None):
    d1 = _gamma1_intermediates(mycc, t1, t2, l1, l2, eris)
    d2 = _gamma2_intermediates(mycc, t1, t2, l1, l2, eris)
    return gccsd_rdm._make_rdm2(mycc, d1, d2, True, True)


if __name__ == '__main__':
    from pyscf import gto
    from pyscf import scf
    from pyscf import ao2mo
    from pyscf import cc

    mol = gto.Mole()
    mol.atom = [
        [8 , (0. , 0.     , 0.)],
        [1 , (0. , -.957 , .587)],
        [1 , (0.2,  .757 , .487)]]
    mol.basis = '631g'
    mol.build()
    mf0 = mf = scf.RHF(mol).run(conv_tol=1.)
    mf = scf.addons.convert_to_ghf(mf)
    mycc = cc.GCCSD(mf)
    eris = mycc.ao2mo()

    from pyscf.cc import ccsd_t_lambda_slow as ccsd_t_lambda
    from pyscf.cc import ccsd_t_rdm_slow as ccsd_t_rdm
    mycc0 = cc.CCSD(mf0)
    eris0 = mycc0.ao2mo()
    mycc0.kernel(eris=eris0)
    t1 = mycc0.t1
    t2 = mycc0.t2
    imds = ccsd_t_lambda.make_intermediates(mycc0, t1, t2, eris0)
    l1, l2 = ccsd_t_lambda.update_lambda(mycc0, t1, t2, t1, t2, eris0, imds)
    dm1ref = ccsd_t_rdm.make_rdm1(mycc0, t1, t2, l1, l2, eris0)
    dm2ref = ccsd_t_rdm.make_rdm2(mycc0, t1, t2, l1, l2, eris0)

    t1 = mycc.spatial2spin(t1, mycc.mo_coeff.orbspin)
    t2 = mycc.spatial2spin(t2, mycc.mo_coeff.orbspin)
    l1 = mycc.spatial2spin(l1, mycc.mo_coeff.orbspin)
    l2 = mycc.spatial2spin(l2, mycc.mo_coeff.orbspin)
    gdm1 = make_rdm1(mycc, t1, t2, l1, l2, eris)
    gdm2 = make_rdm2(mycc, t1, t2, l1, l2, eris)
    idxa = numpy.where(mycc.mo_coeff.orbspin == 0)[0]
    idxb = numpy.where(mycc.mo_coeff.orbspin == 1)[0]

    trdm1 = gdm1[idxa[:,None],idxa]
    trdm1+= gdm1[idxb[:,None],idxb]
    trdm2 = gdm2[idxa[:,None,None,None],idxa[:,None,None],idxa[:,None],idxa]
    trdm2+= gdm2[idxb[:,None,None,None],idxb[:,None,None],idxb[:,None],idxb]
    dm2ab = gdm2[idxa[:,None,None,None],idxa[:,None,None],idxb[:,None],idxb]
    trdm2+= dm2ab
    trdm2+= dm2ab.transpose(2,3,0,1)
    print(abs(trdm1 - dm1ref).max())
    print(abs(trdm2 - dm2ref).max())

#    eri_mo = ao2mo.kernel(mf._eri, mf.mo_coeff, compact=False)
#    nmo = mf.mo_coeff.shape[1]
#    eri_mo = eri_mo.reshape(nmo,nmo,nmo,nmo)
#    dm1 = make_rdm1(mcc, t1, t2, l1, l2, eris=eris)
#    dm2 = make_rdm2(mcc, t1, t2, l1, l2, eris=eris)
#    print(lib.finger(dm1) - 1.2905622485441171)
#    print(lib.finger(dm2) - 6.6064384807461831)
#    h1 = reduce(numpy.dot, (mf.mo_coeff.T, mf.get_hcore(), mf.mo_coeff))
#    e3 =(numpy.einsum('ij,ij->', h1, dm1)
#       + numpy.einsum('ijkl,ijkl->', eri_mo, dm2)*.5 + mf.mol.energy_nuc())

#    mycc = gccsd.GCCSD(mf)
#    ecc, t1, t2 = mycc.kernel()
#    l1, l2 = mycc.solve_lambda()
#    dm1 = make_rdm1(mycc, t1, t2, l1, l2)
#    dm2 = make_rdm2(mycc, t1, t2, l1, l2)
#    nao = mol.nao_nr()
#    mo_a = mf.mo_coeff[:nao]
#    mo_b = mf.mo_coeff[nao:]
#    nmo = mo_a.shape[1]
#    eri = ao2mo.kernel(mf._eri, mo_a+mo_b, compact=False).reshape([nmo]*4)
#    orbspin = mf.mo_coeff.orbspin
#    sym_forbid = (orbspin[:,None] != orbspin)
#    eri[sym_forbid,:,:] = 0
#    eri[:,:,sym_forbid] = 0
#    hcore = scf.RHF(mol).get_hcore()
#    h1 = reduce(numpy.dot, (mo_a.T.conj(), hcore, mo_a))
#    h1+= reduce(numpy.dot, (mo_b.T.conj(), hcore, mo_b))
#    e1 = numpy.einsum('ij,ji', h1, dm1)
#    e1+= numpy.einsum('ijkl,jilk', eri, dm2) * .5
#    e1+= mol.energy_nuc()
#    print(e1 - mycc.e_tot)

