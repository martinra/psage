r"""
Classes describing the Fourier expansion of Jacobi forms of degree `1`
with matrix indices.

AUTHOR :

    - Martin Raum (2012 - 09 - 05) Initial version, based on code for
        Jacobi forms of scalar index.
"""

#===============================================================================
# 
# Copyright (C) 2012 Martin Raum
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
#===============================================================================

from operator import xor
from psage.modform.fourier_expansion_framework.monoidpowerseries.monoidpowerseries_basicmonoids import TrivialCharacterMonoid,\
    TrivialRepresentation
from psage.modform.fourier_expansion_framework.monoidpowerseries.monoidpowerseries_module import EquivariantMonoidPowerSeriesModule
from psage.modform.jacobiforms.jacobiformd1nn_fourierexpansion_cython import creduce, \
                          mult_coeff_int, mult_coeff_int_weak, \
                          mult_coeff_generic, mult_coeff_generic_weak
from sage.matrix.constructor import matrix
from sage.misc.cachefunc import cached_method, cached_function
from sage.misc.functional import isqrt
from sage.misc.latex import latex
from sage.rings.infinity import infinity
from sage.rings.integer import Integer
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.structure.sage_object import SageObject
import itertools
import operator

## TODO: Convert this to a function that calls a class

#===============================================================================
# JacobiFormD1Indices
#===============================================================================

class JacobiFormD1Indices ( UniqueRepresentation ) :
    def __init__(self, L, reduced = True, weak_forms = False) :
        r"""
        INPUT:

            - `L`                -- An even quadratic form, the index of the associated
                                    Jacobi forms.   
            - ``reduced``        -- If ``True`` the reduction of Fourier indices
                                    with respect to the full Jacobi group
                                    will be considered.
            - ``weak_forms``     -- If ``False`` the condition `|L| L^{-1} r**2 <= 4 |L| n`
                                    will be imposed.
        
        NOTE:

            The Fourier expansion of a form is assumed to be indexed
            `\sum c(n,r) q^n \zeta^r` . The indices are pairs `(n, r)`.
        """
        self.__L = L
        self.__reduced = reduced
        self.__weak_forms = weak_forms
        self.__r_module = FreeModule(ZZ, L.matrix().ncols())
        
        # We fix representatives for ZZ^N / L ZZ^N with minimal norm.
        preliminiary_reps = [ s * b
                              for (b, d) in zip(self.__r_module.basis(), L.matrix().echelon_form().diagonal())
                              for s in range(d) ]
        max_norm = max(L(r) for r in preliminary_reps)
        
        short_vectors = L.short_vector_list_up_to_length(max_norm - 1)
        self.__L_span = L.matrix().row_space()
                
        representatives = list()
        for r in preliminary_reps :
            for rrs in short_vectors :
                for rr in rrs :
                    if r - rr in self.__L_span :
                        representatives.append(rr)
                        break
                else :
                    continue
                break
            else :
                representatives.append(r) 
        
        self._r_representatives = representatives
        
        representatives = list()
        for r in self._r_representatives :
            for ri in r :
                if ri > 0 :
                    representatives.append(r)
                    break
                if ri < 0 :
                    break
            else :
                representatives.append(r)

        self._r_reduced_representatives = representatives
        
    def ngens(self) :
        return len(self.gens())
    
    def gen(self, i = 0) :
        if i < self.ngens() :
            return self.gens()[i]
        
        raise ValueError("There is no generator %s" % (i,))
        
    @cached_method
    def gens(self) :
        # FIXME: This is incorrect for almost all indices m 
        return [(1,self.__r_module.zero())] + [(1,r) for r in self.__r_module.basis()]
    
    def jacobi_index(self) :
        return self.__L
    
    def is_commutative(self) :
        return True
    
    def monoid(self) :
        return JacobiFormD1Indices(self.__L, False, self.__weak_forms)
    
    def group(self) :
        r"""
        These are the invertible, integral lower block  triogonal matrices of
        shape (1, N) with bottom right block the identiy matrix `I_N`.
        """
        return "L^1_{0}(ZZ)".format(1 + self.__r_module.rank())
    
    def is_monoid_action(self) :
        r"""
        True if the representation respects the monoid structure.
        """
        return False
    
    def filter(self, bound) :
        return JacobiFormD1Filter(bound, self.__L, self.__reduced, self.__weak_forms)
    
    def filter_all(self) :
        return JacobiFormD1Filter(infinity, self.__L, self.__reduced, self.__weak_forms)
    
    def minimal_composition_filter(self, ls, rs) :
        return JacobiFormD1Filter(   min([k[0] for k in ls])
                                   + min([k[0] for k in rs]),
                                   self.__L, self.__reduced, self.__weak_forms ) 
    
    def _reduction_function(self) :
        return self.reduce
    
    def reduce(self, s) :
        (n, r) = s
        # find a representative that corresponds to s
        for rred in self._r_representatives :
            if r - rred in self.__L_span :
                break
        else :
            raise RuntimeError( "Could not find reduced r" )
        
        ## TODO: Do the computations again and check whether this is right
        la = self.__L_span.coordinates(r - rred)
        
        nred = n - self.__L(la) + sum(map(operator.mul, la, r))
        
        s = 1
        for ri in rred :
            if ri > 0 :
                break
            if ri < 0 :
                rred = -rred
                s = -1
                break
        
        return ((nred, rred), s)
    
    def decompositions(self, s) :
        raise NotImplementedError()
            
    def zero_element(self) :
        return (0,self.__r_module.zero())
    
    def __contains__(self, k) :
        try :
            (n, r) = k
        except TypeError:
            return False
        
        return isinstance(n, (int, Integer)) and r in self.__r_module
    
    def __cmp__(self, other) :
        c = cmp(type(self), type(other))
        
        if c == 0 :
            c = cmp(self.__reduced, other.__reduced)
        if c == 0 :
            c = cmp(self.__weak_forms, other.__weak_forms)
        if c == 0 :
            c = cmp(self.__L, other.__L)
        
        return c

    def __hash__(self) :
        return reduce(xor, [hash(self.__L), hash(self.__reduced),
                            hash(self.__weak_forms)])
    
    def _repr_(self) :
        return "Jacobi Fourier indices for index {0} forms".format(self.__L)
    
    def _latex_(self) :
        return r"\text{{Jacobi Fourier indices for index ${0}$ forms}}".format(latex(self.__L),)
        
#===============================================================================
# JacobiFormD1Filter
#===============================================================================

class JacobiFormD1NNFilter ( SageObject ) :
    r"""
    The filter which will consider the index `n` in the normal
    notation `\sum c(n,r) q^n \zeta^r`.
    """
    
    def __init__(self, bound, L, reduced = True, weak_forms = False) :
        r"""
        INPUT:

            - ``bound``          -- A natural number or exceptionally
                                    infinity reflection the bound for n.

            - `L`                -- An even quadratic form, the index of the associated
                                    Jacobi forms.   
            - ``reduced``        -- If ``True`` the reduction of Fourier indices
                                    with respect to the full Jacobi group
                                    will be considered.
            - ``weak_forms``     -- If ``False`` the condition `|L| L^{-1} r**2 <= 4 |L| n`
                                    will be imposed.

        NOTE:

            The Fourier expansion of a form is assumed to be indexed
            `\sum c(n,r) q^n \zeta^r` . The indices are pairs `(n, r)`.
        """
        self.__L = L
        self.__Ladj = QuadraticForm( L.matrix().adjoint() )
        if isinstance(bound, JacobiFormD1Filter) :
            bound = bound.index()
        self.__bound = bound
        self.__reduced = reduced
        self.__weak_forms = weak_forms
        
        self.__monoid = JacobiFormD1Indices(L, reduced, weak_forms)
        
    def jacobi_index(self) :
        return self.__L
    
    def is_reduced(self) :
        return self.__reduced
    
    def is_weak_filter(self) :
        """
        Return whether this is a filter for weak Jacobi forms or not.
        """
        return self.__weak_forms
    
    def filter_all(self) :
        return JacobiFormD1Filter(infinity, self.__L, self.__reduced, self.__weak_forms)

    def zero_filter(self) :
        return JacobiFormD1Filter(0, self.__L, self.__reduced, self.__weak_forms)
    
    def is_infinite(self) :
        return self.__bound is infinity
    
    def is_all(self) :
        return self.is_infinite()
    
    def index(self) :
        return self.__bound
    
    def __contains__(self, k) :
        if self.__weak_forms :
            raise NotImplementedError()
        
        L = self.__L
        
        (n, r) = k
        
        if ( self.__Ladj(r) > 4 * L.det() * n ## TODO + m**2
             if self.__weak_forms
             else self.__Ladj(r) > 4 * self.__L.det() * n ) :
            return False
        
        if n < self.__bound :
            return True
        elif self.__reduced :
            return self.__monoid.reduce(k)[0][0] < self.__bound
        
        return False
        
    def __iter__(self) :
        return itertools.chain(self.iter_indefinite_forms(),
                               self.iter_positive_forms())
    
    def iter_positive_forms(self) :
        if self.__weak_forms :
            raise NotImplementedError()
        
        fm = 4 * self.__m
        if self.__reduced :
            for n in xrange(1, self.__bound) :
                for r in self.__monoid._r_reduced_representatives :
                    if (n, r) in self :
                        yield (n, r)
        else :
            for n in xrange(1, self.__bound) :
                for rs in self.__Ladj.short_vector_list_up_to_length(2 * self.__L.det() * n) :
                    for r in rs :
                        yield (n, r)
                    
        raise StopIteration
    
    def iter_indefinite_forms(self) :
        if self.__weak_forms :
            raise NotImplementedError()
        
        if self.__reduced :
            for r in xrange(0, min(self.__m + 1,
                                   isqrt((self.__bound - 1) * fm) + 1) ) :
                if fm.divides(r**2) :
                    yield (r**2 // fm, r)
        else :
            short_vectors = self.__Ladj(2 * self.__L.det() * (self.__bound - 1) + 1)
            for n in xrange(0, self.__bound) :
                for r in short_vectors[n] :
                    yield(n, r)

        raise StopIteration
    
    def __cmp__(self, other) :
        c = cmp(type(self), type(other))
        
        if c == 0 :
            c = cmp(self.__reduced, other.__reduced)
        if c == 0 :
            c = cmp(self.__weak_forms, other.__weak_forms)
        if c == 0 :
            c = cmp(self.__L, other.__L)
        if c == 0 :
            c = cmp(self.__bound, other.__bound)
        
        return c
    
    def __hash__(self) :
        return reduce( xor, map(hash, [ self.__reduced, self.__weak_forms,
                                        self.__L, self.__bound ]) )

    def _repr_(self) :
        return "Jacobi precision {0}".format(self.__bound)
    
    def _latex_(self) :
        return r"\text{{Jacobi precision ${0}$}}".format(latex(self.__bound))

#===============================================================================
# JacobiD1FourierExpansionModule
#===============================================================================

def JacobiD1FourierExpansionModule(K, L, weak_forms = False) :
        r"""
        INPUT:

            - `L`                -- The index of the associated Jacobi forms.
            - ``weak_forms``     -- If ``False`` the condition `|L| L^{-1} r**2 <= 4 |L| n`
                                    will be imposed.
        """
        indices = JacobiFormD1Indices(L, weak_forms = weak_forms)
        R = EquivariantMonoidPowerSeriesModule(
             indices,
             TrivialCharacterMonoid(indices.group(), ZZ),
             TrivialRepresentation(indices.group(), K) )
            
        return R
