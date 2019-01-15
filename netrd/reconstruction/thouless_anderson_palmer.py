"""
thouless_anderson_palmer.py
---------------------
Reconstruction of graphs using a Thouless-Anderson-Palmer 
mean field approximation
author: Brennan Klein
email: brennanjamesklein at gmail dot com
submitted as part of the 2019 NetSI Collabathon
"""
from .base import BaseReconstructor
import numpy as np
import networkx as nx
import scipy as sp
from scipy import linalg

def cross_cov(a, b):
    """ 
    cross_covariance
    a,b -->  <(a - <a>)(b - <b>)>  (axis=0) 
    """    
    da = a - np.mean(a, axis=0)
    db = b - np.mean(b, axis=0)

    return np.matmul(da.T, db) / a.shape[0]


class ThoulessAndersonPalmerReconstructor(BaseReconstructor):
    def fit(self, ts):
        """
        Given a (N,t) time series, infer inter-node coupling weights using a 
        Thouless-Anderson-Palmer mean field approximation. 
        After [this tutorial]
        (https://github.com/nihcompmed/network-inference/blob/master/sphinx/codesource/inference.py) 
        in python.

        From the paper: "Similar to naive mean field, TAP works well only in
        the regime of large sample sizes and small coupling variability. 
        However, this method leads to poor inference results in the regime 
        of small sample sizes and/or large coupling variability."
        
        Params
        ------
        ts (np.ndarray): Array consisting of $T$ observations from $N$ sensors.
        
        Returns
        -------
        G (nx.Graph or nx.DiGraph): a reconstructed graph.

        """
        
        N, t = np.shape(ts)             # N nodes, length t
        m = np.mean(ts, axis=1)         # empirical value

        # A matrix
        A = 1 - m**2 
        A_inv = np.diag(1/A)
        A = np.diag(A)

        ds = ts.T - m                   # equal time correlation
        C = np.cov(ds, rowvar=False, bias=True)
        C_inv = linalg.inv(C)
        
        s1 = ts[:,1:]                   # one-step-delayed correlation
        ds1 = s1.T - np.mean(s1, axis=1)
        D = cross_cov(ds1,ds[:-1])    
        
        # predict naive mean field W:
        B     = np.dot(D, C_inv)
        W_NMF = np.dot(A_inv, B)

        # TAP part: solving for Fi in the following equation
        # F(1-F)**2) = (1-m**2)sum_j W_NMF**2(1-m**2) ==> 0<F<1

        step  = 0.001
        nloop = int(0.33/step) + 2 

        W2_NMF = W_NMF**2

        temp = np.empty(N)
        F    = np.empty(N)

        for i in range(N):
            temp[i] = (1 - m[i]**2) * np.sum( W2_NMF[i,:] * (1 - m[:]**2) )

            y=-1. ; iloop=0
            
            while y < 0 and iloop < nloop:
                x = iloop * step
                y = x * (1-x)**2 - temp[i]
                iloop += 1

            F[i] = x

        # A_TAP matrix
        A_TAP = np.empty(N)
        for i in range(N):
            A_TAP[i] = A[i,i] * (1 - F[i])

        A_TAP_inv = np.diag( 1 / A_TAP )
        
        # predict W:
        W = np.dot(A_TAP_inv, B)

        # construct the network
        self.results['graph'] = nx.from_numpy_array(W)
        self.results['matrix'] = W
        G = self.results['graph']

        return G